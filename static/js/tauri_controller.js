/**
 * Tauri Controller Bridge
 *
 * Provides Tauri-only clicker semantics for the classroom workflow.
 * This module only activates when running inside a Tauri shell.
 */

class TauriController {
    constructor() {
        this.isTauri = this.detectTauri();
        this.currentMode = this.modeForTab(typeof window !== 'undefined' ? (window.currentTab || 'analysis') : 'analysis');
        this.pronunciationErrors = [];
        this.currentErrorIndex = -1;
        this.prosodySamples = [];
        this.currentSampleIndex = -1;
        this.isRecording = false;

        if (this.isTauri) {
            this.init();
        }
    }

    /**
   * Map UI tab name to clicker mode
   */
    modeForTab(tabName) {
        if (tabName === 'analysis') return 'pronunciation';
        if (tabName === 'prosody') return 'prosody';
        return null;
    }

    /**
   * Detect if running inside Tauri
   */
    detectTauri() {
        return typeof window !== 'undefined' &&
           (window.__SPEECH_GUIDER_TAURI__ === true || window.__TAURI__ !== undefined);
    }

    /**
   * Initialize the controller
   */
    init() {
        console.log('[TauriController] Initializing in Tauri mode');

        this.currentMode = this.modeForTab(window.currentTab || 'analysis');
        window.addEventListener('speechguider:tabchange', (event) => {
            this.currentMode = this.modeForTab(event.detail);
        });

        // Set up clicker input
        this.setupClickerInput();
    }

    /**
   * Handle launch events from menu bar
   */
    handleLaunch(mode) {
        switch (mode) {
            case 'pronunciation':
                this.launchPronunciation();
                break;
            case 'comparison':
                this.currentMode = null;
                window.switchTab?.('comparison');
                break;
            case 'prosody':
                this.launchProsody();
                break;
            default:
                console.warn('[TauriController] Unknown launch mode:', mode);
        }
    }

    /**
   * Launch pronunciation mode
   */
    launchPronunciation() {
        console.log('[TauriController] Launching pronunciation mode');
        this.currentMode = 'pronunciation';

        // Switch to analysis tab
        if (window.switchTab) {
            window.switchTab('analysis');
        }

        // Reset state
        this.pronunciationErrors = window.currentErrors || [];
        this.currentErrorIndex = -1;
    }

    /**
   * Launch prosody mode
   */
    launchProsody() {
        console.log('[TauriController] Launching prosody mode');
        this.currentMode = 'prosody';

        // Switch to prosody tab
        if (window.switchTab) {
            window.switchTab('prosody');
        }

        // Reset state
        this.prosodySamples = [];
        this.currentSampleIndex = -1;
    }

    /**
   * Check whether keyboard/clicker shortcuts should be ignored for this event
   */
    shouldIgnoreKeyEvent(event) {
        if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) {
            return true;
        }
        return Boolean(event.target?.closest?.('input, textarea, select, [contenteditable="true"]'));
    }

    /**
   * Set up clicker input (Left, Right, Tab)
   */
    setupClickerInput() {
        let tabDownTime = null;
        const TAB_HOLD_THRESHOLD = 200; // ms

        document.addEventListener('keydown', (event) => {
            if (!this.currentMode || window.currentTab === 'comparison') return;
            if (this.shouldIgnoreKeyEvent(event)) return;

            switch (event.key) {
                case 'ArrowLeft':
                    event.preventDefault();
                    this.handlePrevious();
                    break;

                case 'ArrowRight':
                    event.preventDefault();
                    this.handleNext();
                    break;

                case 'Tab':
                    event.preventDefault();
                    if (!this.isRecording && tabDownTime === null) {
                        tabDownTime = Date.now();
                        this.handleRecordPress();
                    }
                    break;
            }
        });

        document.addEventListener('keyup', (event) => {
            if (!this.currentMode || window.currentTab === 'comparison') return;

            if (event.key === 'Tab' && this.isRecording) {
                const holdDuration = tabDownTime !== null ? (Date.now() - tabDownTime) : TAB_HOLD_THRESHOLD;
                tabDownTime = null;

                this.handleRecordRelease();
                if (holdDuration < TAB_HOLD_THRESHOLD) {
                    // Short tap - also notify primary action handler after stopping recording cleanly
                    this.handlePrimaryAction();
                }
            }
        });
    }

    /**
   * Handle 'previous' clicker action
   */
    handlePrevious() {
        console.log('[TauriController] Previous action in', this.currentMode);

        switch (this.currentMode) {
            case 'pronunciation':
                this.previousPronunciationError();
                break;
            case 'prosody':
                this.previousProsodySample();
                break;
        }
    }

    /**
   * Handle 'next' clicker action
   */
    handleNext() {
        console.log('[TauriController] Next action in', this.currentMode);

        switch (this.currentMode) {
            case 'pronunciation':
                this.nextPronunciationError();
                break;
            case 'prosody':
                this.nextProsodySample();
                break;
        }
    }

    /**
   * Handle record press
   */
    handleRecordPress() {
        console.log('[TauriController] Record press in', this.currentMode);

        if (this.isRecording) return;
        this.isRecording = true;

        switch (this.currentMode) {
            case 'pronunciation':
                this.startPronunciationRecording();
                break;
            case 'prosody':
                this.startProsodyRecording();
                break;
        }
    }

    /**
   * Handle record release
   */
    handleRecordRelease() {
        console.log('[TauriController] Record release in', this.currentMode);

        if (!this.isRecording) return;
        this.isRecording = false;

        switch (this.currentMode) {
            case 'pronunciation':
                this.stopPronunciationRecording();
                break;
            case 'prosody':
                this.stopProsodyRecording();
                break;
        }
    }

    /**
   * Handle primary action (for non-recording modes)
   */
    handlePrimaryAction() {
        console.log('[TauriController] Primary action in', this.currentMode);
    }

    // ========== PRONUNCIATION MODE ==========

    getPronunciationErrors() {
        if (Array.isArray(window.currentErrors)) {
            this.pronunciationErrors = window.currentErrors;
            return window.currentErrors;
        }
        return this.pronunciationErrors || [];
    }

    previousPronunciationError() {
        const errors = this.getPronunciationErrors();
        if (!errors || errors.length === 0) {
            console.log('[TauriController] No pronunciation errors available');
            return;
        }

        this.currentErrorIndex--;
        if (this.currentErrorIndex < 0) {
            this.currentErrorIndex = errors.length - 1;
        }

        this.selectPronunciationError(this.currentErrorIndex);
    }

    nextPronunciationError() {
        const errors = this.getPronunciationErrors();
        if (!errors || errors.length === 0) {
            console.log('[TauriController] No pronunciation errors available');
            return;
        }

        this.currentErrorIndex++;
        if (this.currentErrorIndex >= errors.length) {
            this.currentErrorIndex = 0;
        }

        this.selectPronunciationError(this.currentErrorIndex);
    }

    selectPronunciationError(index) {
        if (window.selectError) {
            window.selectError(index);
        }
    }

    startPronunciationRecording() {
        if (window.recorder?.startRecording) {
            window.recorder.startRecording();
        }
    }

    stopPronunciationRecording() {
        if (window.recorder?.stopRecording) {
            window.recorder.stopRecording();
        }
        this.currentErrorIndex = -1;
    }

    // ========== PROSODY MODE ==========

    previousProsodySample() {
        const samples = this.getProsodySamples();

        if (samples.length < 2) {
            console.log('[TauriController] Prosody navigation inert: need at least 2 samples');
            return;
        }

        this.currentSampleIndex--;
        if (this.currentSampleIndex < 0) {
            this.currentSampleIndex = samples.length - 1;
        }

        this.selectProsodySample(this.currentSampleIndex);
    }

    nextProsodySample() {
        const samples = this.getProsodySamples();

        if (samples.length < 2) {
            console.log('[TauriController] Prosody navigation inert: need at least 2 samples');
            return;
        }

        this.currentSampleIndex++;
        if (this.currentSampleIndex >= samples.length) {
            this.currentSampleIndex = 0;
        }

        this.selectProsodySample(this.currentSampleIndex);
    }

    getProsodySamples() {
    // Get samples from prosody lab history or current recording
        if (window.prosodyLabRecorder?.loadHistory) {
            return window.prosodyLabRecorder.loadHistory();
        }
        return [];
    }

    selectProsodySample(index) {
    // Navigate to sample in prosody UI
        const samples = this.getProsodySamples();
        if (samples[index]) {
            // Focus or select the sample
            console.log('[TauriController] Selected prosody sample:', index);
        }
    }

    startProsodyRecording() {
        if (window.prosodyLabRecorder?.startRecording) {
            window.prosodyLabRecorder.startRecording();
        }
    }

    stopProsodyRecording() {
        if (window.prosodyLabRecorder?.stopRecording) {
            window.prosodyLabRecorder.stopRecording();
        }
    }
}

// Initialize the controller when DOM is ready
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        window.tauriController = new TauriController();
    });
}

export { TauriController };
