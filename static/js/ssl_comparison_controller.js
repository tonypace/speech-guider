/**
 * SSL Comparison Controller - Manages side-by-side articulatory playback
 * 
 * Handles two timelines (reference + student) with synchronized or independent playback.
 * Provides audio editing controls: play/pause, scrub, speed, zoom, loop.
 * Feeds frames to existing SVG renderer without modifying renderer geometry.
 */

class SSLComparisonController {
  constructor(options = {}) {
    this.referenceFrames = options.referenceFrames || [];
    this.studentFrames = options.studentFrames || [];
    this.referenceAudio = options.referenceAudio || null;
    this.studentAudio = options.studentAudio || null;
    this.audioSampleRate = options.audioSampleRate || 8000;
    this.frameRate = options.frameRate || 50;

    // Timeline state
    this.referenceTime = 0;
    this.studentTime = 0;
    this.isPlaying = { reference: false, student: false };
    this.playbackSpeed = options.defaultSpeed || 1.0;
    this.linkedPlayheads = options.linkedPlayheads ?? false;
    this.zoomWindow = { start: 0, end: 1 }; // 0-1 normalized

    // Loop region
    this.loopRegion = { enabled: false, start: 0, end: 0 };

    // Audio contexts
    this.audioContext = null;
    this.audioBuffers = { reference: null, student: null };
    this.audioSources = { reference: null, student: null };
    this.startTimes = { reference: 0, student: 0 };
    this.pauseOffsets = { reference: 0, student: 0 };

    // Frame callbacks
    this.onReferenceFrame = options.onReferenceFrame || (() => {});
    this.onStudentFrame = options.onStudentFrame || (() => {});
    this.onTimeUpdate = options.onTimeUpdate || (() => {});
    this.onPlayStateChange = options.onPlayStateChange || (() => {});

    // Animation frame ID for playback loop
    this.animationFrameId = null;
  }

  /**
   * Initialize or resume AudioContext
   */
  initAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  /**
   * Load base64 audio data and decode to AudioBuffer
   */
  async loadAudio(base64Audio, type) {
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const ctx = this.initAudioContext();
    const buffer = await ctx.decodeAudioData(bytes.buffer);
    this.audioBuffers[type] = buffer;
    return buffer;
  }

  /**
   * Get current duration for a track
   */
  getDuration(type) {
    if (type === 'reference') {
      return this.referenceFrames.length / this.frameRate;
    } else {
      return this.studentFrames.length / this.frameRate;
    }
  }

  /**
   * Get current frame index for a track at given time
   */
  getFrameIndex(type, time) {
    const frameIdx = Math.floor(time * this.frameRate);
    const frames = type === 'reference' ? this.referenceFrames : this.studentFrames;
    return Math.max(0, Math.min(frameIdx, frames.length - 1));
  }

  /**
   * Get frame data for a track at current time
   */
  getCurrentFrame(type) {
    const time = type === 'reference' ? this.referenceTime : this.studentTime;
    const frameIdx = this.getFrameIndex(type, time);
    const frames = type === 'reference' ? this.referenceFrames : this.studentFrames;
    return frames[frameIdx] || null;
  }

  /**
   * Set time for a specific track
   */
  setTime(type, time, updateLinked = true) {
    const duration = this.getDuration(type);
    const clampedTime = Math.max(0, Math.min(time, duration));

    if (type === 'reference') {
      this.referenceTime = clampedTime;
    } else {
      this.studentTime = clampedTime;
    }

    // Update linked playhead
    if (updateLinked && this.linkedPlayheads) {
      const otherType = type === 'reference' ? 'student' : 'reference';
      const otherDuration = this.getDuration(otherType);
      const relativePosition = duration > 0 ? clampedTime / duration : 0;
      const otherTime = relativePosition * otherDuration;
      this.setTime(otherType, otherTime, false);
    }

    // Emit frame update
    this.emitFrameUpdate(type);
    this.onTimeUpdate(this.referenceTime, this.studentTime);
  }

  /**
   * Emit frame update for a track
   */
  emitFrameUpdate(type) {
    const frame = this.getCurrentFrame(type);
    if (frame) {
      if (type === 'reference') {
        this.onReferenceFrame(frame, this.referenceTime);
      } else {
        this.onStudentFrame(frame, this.studentTime);
      }
    }
  }

  /**
   * Play a specific track
   */
  play(type) {
    if (this.isPlaying[type]) return;

    const buffer = this.audioBuffers[type];
    if (!buffer) {
      console.warn(`[SSLComparisonController] No audio buffer for ${type}`);
      // Still allow frame-only playback without audio
    }

    this.isPlaying[type] = true;
    this.startTimes[type] = this.audioContext ? this.audioContext.currentTime : 0;

    if (buffer && this.audioContext) {
      // Create and start audio source
      this.audioSources[type] = this.audioContext.createBufferSource();
      this.audioSources[type].buffer = buffer;
      this.audioSources[type].connect(this.audioContext.destination);

      // Start at current offset
      const currentTime = type === 'reference' ? this.referenceTime : this.studentTime;
      this.audioSources[type].start(0, currentTime);
    }

    // Start animation loop if not already running
    if (!this.animationFrameId) {
      this.animationLoop();
    }

    this.onPlayStateChange(this.isPlaying.reference, this.isPlaying.student);
  }

  /**
   * Pause a specific track
   */
  pause(type) {
    if (!this.isPlaying[type]) return;

    this.isPlaying[type] = false;

    // Stop audio source
    if (this.audioSources[type]) {
      try {
        this.audioSources[type].stop();
      } catch (e) {
        // Source might already be stopped
      }
      this.audioSources[type] = null;
    }

    // Store pause offset
    const currentTime = type === 'reference' ? this.referenceTime : this.studentTime;
    this.pauseOffsets[type] = currentTime;

    // Check if both paused
    if (!this.isPlaying.reference && !this.isPlaying.student) {
      this.stopAnimationLoop();
    }

    this.onPlayStateChange(this.isPlaying.reference, this.isPlaying.student);
  }

  /**
   * Toggle play/pause for a track
   */
  togglePlay(type) {
    if (this.isPlaying[type]) {
      this.pause(type);
    } else {
      this.play(type);
    }
  }

  /**
   * Stop both tracks
   */
  stop() {
    this.pause('reference');
    this.pause('student');
    this.setTime('reference', 0);
    this.setTime('student', 0);
  }

  /**
   * Main animation loop - called via requestAnimationFrame
   */
  animationLoop() {
    if (!this.isPlaying.reference && !this.isPlaying.student) {
      this.stopAnimationLoop();
      return;
    }

    const now = this.audioContext ? this.audioContext.currentTime : performance.now() / 1000;
    const deltaTime = (now - (this.lastFrameTime || now)) * this.playbackSpeed;
    this.lastFrameTime = now;

    // Update reference track
    if (this.isPlaying.reference) {
      const refDuration = this.getDuration('reference');
      let newTime = this.referenceTime + deltaTime;

      // Handle loop
      if (this.loopRegion.enabled && newTime >= this.loopRegion.end) {
        newTime = this.loopRegion.start;
        this.startTimes.reference = now - (newTime / this.playbackSpeed);
      }

      // Check if finished
      if (newTime >= refDuration) {
        this.pause('reference');
        newTime = refDuration;
      }

      this.referenceTime = newTime;
    }

    // Update student track
    if (this.isPlaying.student) {
      const studentDuration = this.getDuration('student');
      let newTime = this.studentTime + deltaTime;

      // Handle loop
      if (this.loopRegion.enabled && newTime >= this.loopRegion.end) {
        newTime = this.loopRegion.start;
        this.startTimes.student = now - (newTime / this.playbackSpeed);
      }

      // Check if finished
      if (newTime >= studentDuration) {
        this.pause('student');
        newTime = studentDuration;
      }

      this.studentTime = newTime;
    }

    // Sync linked playheads
    if (this.linkedPlayheads) {
      if (this.isPlaying.reference && !this.isPlaying.student) {
        const refDuration = this.getDuration('reference');
        const studentDuration = this.getDuration('student');
        const relativePos = refDuration > 0 ? this.referenceTime / refDuration : 0;
        this.studentTime = relativePos * studentDuration;
      } else if (this.isPlaying.student && !this.isPlaying.reference) {
        const studentDuration = this.getDuration('student');
        const refDuration = this.getDuration('reference');
        const relativePos = studentDuration > 0 ? this.studentTime / studentDuration : 0;
        this.referenceTime = relativePos * refDuration;
      }
    }

    // Emit updates
    this.emitFrameUpdate('reference');
    this.emitFrameUpdate('student');
    this.onTimeUpdate(this.referenceTime, this.studentTime);

    this.animationFrameId = requestAnimationFrame(() => this.animationLoop());
  }

  /**
   * Stop the animation loop
   */
  stopAnimationLoop() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.lastFrameTime = null;
  }

  /**
   * Set playback speed (0.25x - 1.25x)
   */
  setSpeed(speed) {
    const validSpeeds = [0.25, 0.5, 0.75, 1, 1.25];
    this.playbackSpeed = validSpeeds.includes(speed) ? speed : 1.0;
  }

  /**
   * Set zoom window (normalized 0-1)
   */
  setZoomWindow(start, end) {
    this.zoomWindow = {
      start: Math.max(0, Math.min(start, 1)),
      end: Math.max(0, Math.min(end, 1)),
    };
  }

  /**
   * Get visible time range based on zoom window
   */
  getVisibleTimeRange(type) {
    const duration = this.getDuration(type);
    return {
      start: this.zoomWindow.start * duration,
      end: this.zoomWindow.end * duration,
    };
  }

  /**
   * Set loop region
   */
  setLoopRegion(start, end, enabled = true) {
    const duration = Math.max(
      this.getDuration('reference'),
      this.getDuration('student')
    );
    this.loopRegion = {
      enabled,
      start: Math.max(0, Math.min(start, duration)),
      end: Math.max(0, Math.min(end, duration)),
    };
  }

  /**
   * Toggle linked playheads
   */
  setLinkedPlayheads(linked) {
    this.linkedPlayheads = linked;
    if (linked) {
      // Sync student to reference when enabling link
      const refDuration = this.getDuration('reference');
      const studentDuration = this.getDuration('student');
      const relativePos = refDuration > 0 ? this.referenceTime / refDuration : 0;
      this.setTime('student', relativePos * studentDuration, false);
    }
  }

  /**
   * Load reference data (frames + audio)
   */
  loadReference(frames, base64Audio) {
    this.referenceFrames = frames || [];
    if (base64Audio) {
      return this.loadAudio(base64Audio, 'reference');
    }
    return Promise.resolve();
  }

  /**
   * Load student data (frames + audio)
   */
  loadStudent(frames, base64Audio) {
    this.studentFrames = frames || [];
    if (base64Audio) {
      return this.loadAudio(base64Audio, 'student');
    }
    return Promise.resolve();
  }

  /**
   * Clear all data
   */
  clear() {
    this.stop();
    this.referenceFrames = [];
    this.studentFrames = [];
    this.referenceAudio = null;
    this.studentAudio = null;
    this.audioBuffers = { reference: null, student: null };
    this.pauseOffsets = { reference: 0, student: 0 };
    this.zoomWindow = { start: 0, end: 1 };
    this.loopRegion = { enabled: false, start: 0, end: 0 };
  }

  /**
   * Get current state for UI updates
   */
  getState() {
    return {
      reference: {
        time: this.referenceTime,
        duration: this.getDuration('reference'),
        isPlaying: this.isPlaying.reference,
        currentFrame: this.getCurrentFrame('reference'),
      },
      student: {
        time: this.studentTime,
        duration: this.getDuration('student'),
        isPlaying: this.isPlaying.student,
        currentFrame: this.getCurrentFrame('student'),
      },
      speed: this.playbackSpeed,
      linked: this.linkedPlayheads,
      zoom: this.zoomWindow,
      loop: this.loopRegion,
    };
  }
}

// Export for module usage
export { SSLComparisonController };

// Also attach to window for global access
window.SSLComparisonController = SSLComparisonController;
