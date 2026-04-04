/**
 * Tauri Controller Bridge
 * 
 * Provides Tauri-only clicker semantics for the classroom workflow.
 * This module only activates when running inside a Tauri shell.
 */

class TauriController {
  constructor() {
    this.isTauri = this.detectTauri();
    this.currentMode = null;
    this.pronunciationErrors = [];
    this.currentErrorIndex = -1;
    this.prosodySamples = [];
    this.currentSampleIndex = -1;
    this.animationPhonemes = [];
    this.currentPhonemeIndex = -1;
    this.isRecording = false;
    
    if (this.isTauri) {
      this.init();
    }
  }
  
  /**
   * Detect if running inside Tauri
   */
  detectTauri() {
    return typeof window !== 'undefined' && 
           window.__TAURI__ !== undefined;
  }
  
  /**
   * Initialize the controller
   */
  init() {
    console.log('[TauriController] Initializing in Tauri mode');
    
    // Listen for menu bar launch events
    this.setupMenuListeners();
    
    // Set up clicker input
    this.setupClickerInput();
    
    // Build phoneme list for animation mode
    this.buildPhonemeList();
  }
  
  /**
   * Listen for Tauri menu bar events
   */
  setupMenuListeners() {
    if (window.__TAURI__?.event) {
      // Handle launch events from menu bar
      window.__TAURI__.event.listen('speechguider:launch', (event) => {
        console.log('[TauriController] Launch event:', event.payload);
        this.handleLaunch(event.payload);
      });
    }
  }
  
  /**
   * Handle launch events from menu bar
   */
  handleLaunch(mode) {
    switch (mode) {
      case 'pronunciation':
        this.launchPronunciation();
        break;
      case 'prosody':
        this.launchProsody();
        break;
      case 'animation':
        this.launchAnimation();
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
   * Launch animation mode
   */
  launchAnimation() {
    console.log('[TauriController] Launching animation mode');
    this.currentMode = 'animation';
    
    // Switch to animation tab
    if (window.switchTab) {
      window.switchTab('animation');
    }
    
    // Reset state
    this.currentPhonemeIndex = -1;
  }
  
  /**
   * Set up clicker input (Left, Right, Tab)
   */
  setupClickerInput() {
    let tabDownTime = null;
    const TAB_HOLD_THRESHOLD = 200; // ms
    
    document.addEventListener('keydown', (event) => {
      if (!this.currentMode) return;
      
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
      if (!this.currentMode) return;
      
      if (event.key === 'Tab' && this.isRecording) {
        const holdDuration = Date.now() - tabDownTime;
        tabDownTime = null;
        
        if (holdDuration >= TAB_HOLD_THRESHOLD) {
          this.handleRecordRelease();
        } else {
          // Short tap - treat as primary action for non-recording modes
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
      case 'animation':
        this.previousAnimationPhoneme();
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
      case 'animation':
        this.nextAnimationPhoneme();
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
    
    switch (this.currentMode) {
      case 'animation':
        this.animateCurrentPhoneme();
        break;
    }
  }
  
  // ========== PRONUNCIATION MODE ==========
  
  previousPronunciationError() {
    if (!this.pronunciationErrors || this.pronunciationErrors.length === 0) {
      console.log('[TauriController] No pronunciation errors available');
      return;
    }
    
    this.currentErrorIndex--;
    if (this.currentErrorIndex < 0) {
      this.currentErrorIndex = this.pronunciationErrors.length - 1;
    }
    
    this.selectPronunciationError(this.currentErrorIndex);
  }
  
  nextPronunciationError() {
    if (!this.pronunciationErrors || this.pronunciationErrors.length === 0) {
      console.log('[TauriController] No pronunciation errors available');
      return;
    }
    
    this.currentErrorIndex++;
    if (this.currentErrorIndex >= this.pronunciationErrors.length) {
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
    
    // After recording, refresh error list
    setTimeout(() => {
      this.pronunciationErrors = window.currentErrors || [];
      this.currentErrorIndex = -1;
    }, 2000);
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
  
  // ========== ANIMATION MODE ==========
  
  buildPhonemeList() {
    // Build list of available phonemes from the phoneme buttons
    this.animationPhonemes = [];
    document.querySelectorAll('.phoneme-btn').forEach((btn) => {
      const phoneme = btn.getAttribute('data-phoneme');
      if (phoneme) {
        this.animationPhonemes.push(phoneme);
      }
    });
  }
  
  previousAnimationPhoneme() {
    if (this.animationPhonemes.length === 0) {
      this.buildPhonemeList();
    }
    
    if (this.animationPhonemes.length === 0) return;
    
    this.currentPhonemeIndex--;
    if (this.currentPhonemeIndex < 0) {
      this.currentPhonemeIndex = this.animationPhonemes.length - 1;
    }
    
    this.selectAnimationPhoneme(this.animationPhonemes[this.currentPhonemeIndex]);
  }
  
  nextAnimationPhoneme() {
    if (this.animationPhonemes.length === 0) {
      this.buildPhonemeList();
    }
    
    if (this.animationPhonemes.length === 0) return;
    
    this.currentPhonemeIndex++;
    if (this.currentPhonemeIndex >= this.animationPhonemes.length) {
      this.currentPhonemeIndex = 0;
    }
    
    this.selectAnimationPhoneme(this.animationPhonemes[this.currentPhonemeIndex]);
  }
  
  selectAnimationPhoneme(phoneme) {
    if (window.selectPhoneme) {
      window.selectPhoneme(phoneme);
      // Animation happens automatically via selectPhoneme
    }
  }
  
  animateCurrentPhoneme() {
    if (this.currentPhonemeIndex >= 0 && 
        this.currentPhonemeIndex < this.animationPhonemes.length) {
      this.selectAnimationPhoneme(this.animationPhonemes[this.currentPhonemeIndex]);
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
