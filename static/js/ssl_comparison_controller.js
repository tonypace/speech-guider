/**
 * SSL Comparison Controller - Manages side-by-side articulatory playback
 * 
 * Handles two timelines (reference + student) with synchronized or independent playback.
 * Provides audio editing controls: play/pause, scrub, speed, zoom, loop.
 * Feeds frames to existing SVG renderer without modifying renderer geometry.
 */

import { encodePcmWav } from './audio_conversion.js';
import { getDurationMatch, measureSpeech } from './comparison_timing.js';

class SSLComparisonController {
    constructor(options = {}) {
        this.destroyed = false;
        this.referenceFrames = options.referenceFrames || [];
        this.studentFrames = options.studentFrames || [];
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

        this.audioContext = null;
        this.tracks = { reference: null, student: null };
        this.studentRate = 1;
        this.durationMatching = false;

        // Frame callbacks
        this.onReferenceFrame = options.onReferenceFrame || (() => {});
        this.onStudentFrame = options.onStudentFrame || (() => {});
        this.onTimeUpdate = options.onTimeUpdate || (() => {});
        this.onPlayStateChange = options.onPlayStateChange || (() => {});
        this.onPlaybackError = options.onPlaybackError || (() => {});

        // Animation frame ID for playback loop
        this.animationFrameId = null;
        this.audioLoadVersions = { reference: 0, student: 0 };
    }

    /**
   * Decode reference and student audio at the analysis sample rate.
   */
    initAudioContext() {
        if (this.destroyed) throw new Error('Playback controller disposed');
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        }
        return this.audioContext;
    }

    getTimingRate(type) {
        return type === 'student' ? this.studentRate : 1;
    }

    /**
   * Get current duration for a track
   */
    getDuration(type) {
        const track = this.tracks[type];
        const frames = type === 'reference' ? this.referenceFrames : this.studentFrames;
        return track ? track.duration / this.getTimingRate(type) : frames.length / this.frameRate;
    }

    getMatchRate() {
        const { reference, student } = this.tracks;
        if (!reference || !student || !student.audio.preservesPitch) return null;
        return getDurationMatch(reference.speech, student.speech, reference.duration, student.duration);
    }

    setDurationMatching(enabled) {
        const rate = enabled ? this.getMatchRate() : null;
        const nextRate = rate ?? 1;
        this.durationMatching = rate !== null;
        if (nextRate !== this.studentRate) {
            this.pause('reference');
            this.pause('student');
            const time = this.studentTime * this.studentRate;
            this.studentRate = nextRate;
            this.setTime('student', time / nextRate);
        }
    }

    /**
   * Get current frame index for a track at given time
   */
    getFrameIndex(type, time) {
        const sourceTime = (this.tracks[type]?.start ?? 0) + time * this.getTimingRate(type);
        const frameIdx = Math.floor((sourceTime + 1e-9) * this.frameRate);
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

        const audio = this.tracks[type]?.audio;
        if (audio) audio.currentTime = clampedTime * this.getTimingRate(type);

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
        const duration = this.getDuration(type);
        if (!duration) return;
        const time = type === 'reference' ? this.referenceTime : this.studentTime;
        if (time >= duration) this.setTime(type, 0);

        this.isPlaying[type] = true;
        const track = this.tracks[type];
        if (track) {
            const { audio } = track;
            audio.playbackRate = this.playbackSpeed * this.getTimingRate(type);
            audio.currentTime = (type === 'reference' ? this.referenceTime : this.studentTime) * this.getTimingRate(type);
            void this.playAudio(type, track);
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

        const audio = this.tracks[type]?.audio;
        if (audio) {
            audio.pause();
            const time = Math.min(audio.currentTime / this.getTimingRate(type), this.getDuration(type));
            if (type === 'reference') this.referenceTime = time;
            else this.studentTime = time;
        }

        // Check if both paused
        if (!this.isPlaying.reference && !this.isPlaying.student) {
            this.stopAnimationLoop();
        }

        this.onPlayStateChange(this.isPlaying.reference, this.isPlaying.student);
    }

    async playAudio(type, track) {
        try {
            await track.audio.play();
        } catch (error) {
            if (error.name === 'AbortError' || this.tracks[type] !== track || !this.isPlaying[type]) return;
            this.pause(type);
            this.onPlaybackError(type);
        }
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

        const now = performance.now() / 1000;
        const deltaTime = (now - (this.lastFrameTime ?? now)) * this.playbackSpeed;
        this.lastFrameTime = now;

        const { reference: playingReference, student: playingStudent } = this.isPlaying;
        for (const type of ['reference', 'student']) {
            this.advanceTrack(type, deltaTime);
        }

        // Sync linked playheads
        if (this.linkedPlayheads) {
            if (playingReference && !playingStudent) {
                const refDuration = this.getDuration('reference');
                const studentDuration = this.getDuration('student');
                const relativePos = refDuration > 0 ? this.referenceTime / refDuration : 0;
                this.studentTime = relativePos * studentDuration;
            } else if (playingStudent && !playingReference) {
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

        if (this.isPlaying.reference || this.isPlaying.student) {
            this.animationFrameId = requestAnimationFrame(() => this.animationLoop());
        }
    }

    advanceTrack(type, deltaTime) {
        if (!this.isPlaying[type]) return;
        const duration = this.getDuration(type);
        const timeKey = type === 'reference' ? 'referenceTime' : 'studentTime';
        const track = this.tracks[type];
        const audio = track?.audio;
        const rate = this.getTimingRate(type);
        let time = audio ? audio.currentTime / rate : this[timeKey] + deltaTime;
        if (audio?.ended) time = duration;
        const { enabled, start, end } = this.loopRegion;
        const loopEnd = Math.min(end, duration);
        if (enabled && loopEnd > start && time >= loopEnd) {
            time = start + ((time - start) % (loopEnd - start));
            if (audio) {
                const ended = audio.ended;
                audio.currentTime = time * rate;
                if (ended) void this.playAudio(type, track);
            }
        }
        this[timeKey] = Math.min(time, duration);
        if (time >= duration) {
            this.pause(type);
            this[timeKey] = duration;
        }
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
   * Set a supported playback speed.
   */
    setSpeed(speed) {
        const validSpeeds = [0.25, 0.3, 0.5, 0.75, 1, 1.25];
        this.playbackSpeed = validSpeeds.includes(speed) ? speed : 1.0;
        for (const [type, track] of Object.entries(this.tracks)) {
            if (track) track.audio.playbackRate = this.playbackSpeed * this.getTimingRate(type);
        }
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
    async loadReference(frames, audio, isCurrent = () => true) {
        return this.loadTrack('reference', frames, audio, isCurrent);
    }

    async loadStudent(frames, audio, isCurrent = () => true) {
        return this.loadTrack('student', frames, audio, isCurrent);
    }

    async loadTrack(type, frames, audio, isCurrent) {
        if (this.destroyed) return false;
        const version = ++this.audioLoadVersions[type];
        let buffer = null;
        if (audio) {
            const bytes = typeof audio === 'string'
                ? Uint8Array.from(atob(audio), char => char.charCodeAt(0)).buffer
                : await audio.arrayBuffer();
            if (this.destroyed || version !== this.audioLoadVersions[type] || !isCurrent()) return false;
            buffer = await this.initAudioContext().decodeAudioData(bytes);
        }
        if (this.destroyed || version !== this.audioLoadVersions[type] || !isCurrent()) return false;
        const track = buffer ? this.createTrack(buffer) : null;
        this.resetTrack(type);
        if (type === 'reference') {
            this.referenceFrames = frames || [];
        } else {
            this.studentFrames = frames || [];
        }
        this.tracks[type] = track;
        this.emitFrameUpdate(type);
        return true;
    }

    createTrack(buffer) {
        const speech = measureSpeech(buffer);
        const start = Math.floor((speech?.start ?? 0) * buffer.sampleRate);
        const end = Math.min(buffer.length, Math.ceil((speech?.end ?? buffer.duration) * buffer.sampleRate));
        // PCM WAV gives both browser engines the same sample bounds and a seekable media clock.
        const url = URL.createObjectURL(encodePcmWav(buffer, end - start, false, start));
        const audio = new Audio();
        if ('preservesPitch' in audio) audio.preservesPitch = true;
        audio.src = url;
        return {
            audio,
            url,
            speech,
            start: start / buffer.sampleRate,
            duration: (end - start) / buffer.sampleRate,
        };
    }

    resetTrack(type) {
        this.setDurationMatching(false);
        this.pause(type);
        this.audioLoadVersions[type]++;
        const track = this.tracks[type];
        if (track) {
            track.audio.removeAttribute('src');
            track.audio.load();
            URL.revokeObjectURL(track.url);
            this.tracks[type] = null;
        }
        if (type === 'reference') this.referenceTime = 0;
        else this.studentTime = 0;
    }

    clearTrack(type) {
        this.resetTrack(type);
        if (type === 'reference') this.referenceFrames = [];
        else this.studentFrames = [];
    }

    /**
   * Clear all data
   */
    clear() {
        this.stop();
        this.resetTrack('reference');
        this.resetTrack('student');
        this.referenceFrames = [];
        this.studentFrames = [];
        this.zoomWindow = { start: 0, end: 1 };
        this.loopRegion = { enabled: false, start: 0, end: 0 };
    }

    /**
   * Get current state for UI updates
   */
    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        this.clear();
        const context = this.audioContext;
        this.audioContext = null;
        if (context && context.state !== 'closed') {
            Promise.resolve(context.close()).catch((error) => console.warn('Audio close failed', error));
        }
    }

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
