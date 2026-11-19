import { trimProsodyHistory, loadHistory, storeRecord, getRoleId, setRoleId, createDesktopHistoryStorage } from './prosody_history.js';
import { listen, releaseCapture } from './capture_resources.js';
import { microphoneError, openMicrophone } from './microphone.js';
import { convertAudioToWav, encodePcmWav } from './audio_conversion.js';
import { escapeHtml } from './ipa_tooltips.js';
import {
    getPhraseById,
    setCustomPhrase,
    alignRecordPairToTetherItems,
    renderVocAlignTetherDiagnosticSVG,
    renderFlowMatrixTrainerSVG,
    ProsodyAudioPlayer,
} from './prosody_rhythm_views.js';

function midiToNoteName(midi) {
    if (midi === null || midi === undefined || Number.isNaN(midi)) {
        return '-';
    }

    const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const rounded = Math.round(midi);
    const note = notes[((rounded % 12) + 12) % 12];
    const octave = Math.floor(rounded / 12) - 1;
    return `${note}${octave}`;
}

function formatMetricValue(value, suffix = '') {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return '—';
    }
    if (typeof value === 'number') {
        return `${value.toFixed(value >= 100 ? 0 : 2)}${suffix}`;
    }
    return `${value}${suffix}`;
}

const BAR_DURATION_SECONDS = 2.0;
const PITCH_MARKER_SIZE = 9;
const ANCHOR_MARKER_SIZE = 11;
const GRACE_NOTE_SIZE = 5;
const MAX_GRACE_NOTES_PER_REGION = 3;
const STRESS_EVERY_N_SYLLABLES = 3;

function detectBeatsPerBar(syllableCount, durationSeconds) {
    if (syllableCount < 4 || durationSeconds <= 0) return 4;
    const syllablesPerSecond = syllableCount / durationSeconds;
    if (syllablesPerSecond > 5) return 8;
    return 4;
}

function snapToGrid(value, gridStep) {
    return Math.round(value / gridStep) * gridStep;
}

function buildNoteTicks(minMidi, maxMidi) {
    const tickVals = [];
    const tickText = [];
    const span = Math.max(1, Math.ceil(maxMidi) - Math.floor(minMidi));
    const step = Math.max(2, Math.ceil(span / 5));
    for (let midi = Math.floor(minMidi); midi <= Math.ceil(maxMidi); midi += step) {
        tickVals.push(midi);
        tickText.push(midiToNoteName(midi));
    }
    return { tickVals, tickText };
}

function chunkIntoBars(pitchTrack, barDuration) {
    if (!pitchTrack || pitchTrack.length === 0) return [];
    const maxTime = pitchTrack[pitchTrack.length - 1].time;
    const barCount = Math.max(1, Math.ceil(maxTime / barDuration));
    const bars = [];
    for (let i = 0; i < barCount; i += 1) {
        const windowStart = i * barDuration;
        const windowEnd = (i + 1) * barDuration;
        const points = pitchTrack.filter((p) => p.time >= windowStart && p.time < windowEnd);
        bars.push({
            index: i,
            startTime: windowStart,
            endTime: Math.min(windowEnd, maxTime),
            duration: Math.min(windowEnd, maxTime) - windowStart,
            points,
        });
    }
    return bars;
}

function classifySyllableStress(syllableOnsets, syllableDetails = null) {
    if (Array.isArray(syllableDetails) && syllableDetails.length > 0) {
        const stressed = [];
        const unstressed = [];
        syllableDetails.forEach((detail) => {
            const t = Number(detail.p_center_time ?? detail.nucleus_time ?? 0);
            if (detail.is_stressed) {
                stressed.push(t);
            } else {
                unstressed.push(t);
            }
        });
        if (stressed.length === 0 && syllableDetails.length > 0) {
            stressed.push(Number(syllableDetails[0].p_center_time ?? syllableDetails[0].nucleus_time ?? 0));
        }
        return { stressed, unstressed };
    }

    if (!syllableOnsets || syllableOnsets.length === 0) return { stressed: [], unstressed: [] };
    const n = STRESS_EVERY_N_SYLLABLES;
    const stressed = [];
    const unstressed = [];
    syllableOnsets.forEach((onset, idx) => {
        if (idx % n === 0) {
            stressed.push(onset);
        } else {
            unstressed.push(onset);
        }
    });
    return { stressed, unstressed };
}

function assignGraceNotesBetween(unstressed, stressed) {
    if (!unstressed.length || !stressed.length) return [];
    const regions = [];
    for (let i = 0; i < stressed.length - 1; i += 1) {
        regions.push({ start: stressed[i], end: stressed[i + 1] });
    }
    if (stressed.length >= 1 && unstressed.length > 0) {
        const lastStressed = stressed[stressed.length - 1];
        regions.push({ start: lastStressed, end: Infinity });
    }
    const graceByRegion = regions.map((region) => {
        const inRegion = unstressed.filter((u) => u > region.start && u < region.end);
        return inRegion.slice(0, MAX_GRACE_NOTES_PER_REGION);
    });
    return graceByRegion.flat();
}

function buildBarTrace(bar, quantizedMidi, localTimes, textValues, anchorTimes, graceTimes) {
    const traces = [];
    if (quantizedMidi.length > 0) {
        traces.push({
            type: 'scatter',
            mode: 'lines+markers',
            x: localTimes,
            y: quantizedMidi,
            line: { color: '#0f0f0f', width: 2 },
            marker: { size: PITCH_MARKER_SIZE, color: '#0f0f0f' },
            text: textValues,
            hovertemplate: '%{text}<extra></extra>',
            name: 'pitch',
            xaxis: `x${bar.index + 1}`,
            yaxis: `y${bar.index + 1}`,
            showlegend: false,
        });
    }
    if (anchorTimes.length > 0) {
        const anchorMidi = anchorTimes.map(() => quantizedMidi.length > 0 ? quantizedMidi[Math.floor(quantizedMidi.length / 2)] : 60);
        traces.push({
            type: 'scatter',
            mode: 'markers',
            x: anchorTimes,
            y: anchorMidi,
            marker: { size: ANCHOR_MARKER_SIZE, color: '#0f0f0f', symbol: 'circle' },
            text: anchorTimes.map((t) => `stressed @ ${t.toFixed(3)}s`),
            hovertemplate: '%{text}<extra></extra>',
            name: 'stressed',
            xaxis: `x${bar.index + 1}`,
            yaxis: `y${bar.index + 1}`,
            showlegend: false,
        });
    }
    if (graceTimes.length > 0) {
        const graceMidi = graceTimes.map(() => quantizedMidi.length > 0 ? quantizedMidi[Math.floor(quantizedMidi.length / 2)] : 60);
        traces.push({
            type: 'scatter',
            mode: 'markers',
            x: graceTimes,
            y: graceMidi,
            marker: { size: GRACE_NOTE_SIZE, color: '#555555', symbol: 'circle' },
            text: graceTimes.map((t) => `unstressed @ ${t.toFixed(3)}s`),
            hovertemplate: '%{text}<extra></extra>',
            name: 'unstressed',
            xaxis: `x${bar.index + 1}`,
            yaxis: `y${bar.index + 1}`,
            showlegend: false,
        });
    }
    return traces;
}

function buildMusicalScoreChart(record, options = {}) {
    const { locked = false, beatsPerBar = 4, zoomLevel = 1.0 } = options;
    const pitchTrack = record?.pitch_track || [];
    const syllableOnsets = (Array.isArray(record?.syllable_p_centers) && record.syllable_p_centers.length > 0)
        ? record.syllable_p_centers
        : (record?.syllable_onsets || []);
    const syllableDetails = record?.syllable_details || null;
    const barDuration = BAR_DURATION_SECONDS / zoomLevel;
    const bars = chunkIntoBars(pitchTrack, barDuration);

    if (bars.length === 0) {
        return { traces: [], layout: {}, frames: [] };
    }
    const { stressed, unstressed } = classifySyllableStress(syllableOnsets, syllableDetails);
    const graceTimes = assignGraceNotesBetween(unstressed, stressed);
    const allMidi = pitchTrack.map((p) => p.midi).filter((m) => m !== null && !Number.isNaN(m));
    const globalMinMidi = allMidi.length ? Math.floor(Math.min(...allMidi)) - 1 : 36;
    const globalMaxMidi = allMidi.length ? Math.ceil(Math.max(...allMidi)) + 1 : 72;
    const { tickVals, tickText } = buildNoteTicks(globalMinMidi, globalMaxMidi);
    const beatInterval = barDuration / beatsPerBar;
    const traces = [];

    bars.forEach((bar) => {
        const localTimes = bar.points.map((p) => p.time - bar.startTime);
        const quantizedMidi = bar.points.map((p) => {
            if (p.midi === null || p.midi === undefined || Number.isNaN(p.midi)) return null;
            return Math.round(p.midi);
        });
        const textValues = bar.points.map((p) => {
            const note = p.note || midiToNoteName(p.midi);
            const f0 = p.f0_hz ? `${p.f0_hz.toFixed(1)} Hz` : 'unvoiced';
            return `${note}<br>${f0}`;
        });
        let anchorTimes = stressed
            .filter((t) => t >= bar.startTime && t < bar.startTime + barDuration)
            .map((t) => {
                const local = t - bar.startTime;
                return locked ? snapToGrid(local, beatInterval) : local;
            });
        let barGraceTimes = graceTimes
            .filter((t) => t >= bar.startTime && t < bar.startTime + barDuration)
            .map((t) => t - bar.startTime);
        const barTraces = buildBarTrace(bar, quantizedMidi, localTimes, textValues, anchorTimes, barGraceTimes);
        traces.push(...barTraces);
    });
    const axesDict = {};
    const gap = bars.length > 1 ? Math.min(0.08, 0.25 / bars.length) : 0;
    const bandHeight = (1 - gap * (bars.length - 1)) / bars.length;
    bars.forEach((bar, idx) => {
        const row = idx + 1;
        const yAxisKey = row === 1 ? 'y' : `y${row}`;
        const xAxisKey = row === 1 ? 'x' : `x${row}`;
        const top = Math.min(1, 1 - idx * (bandHeight + gap));
        const bottom = Math.max(0, top - bandHeight);
        axesDict[`yaxis${row}`] = {
            title: idx === 0 ? 'Note' : '',
            range: [globalMinMidi, globalMaxMidi],
            tickmode: 'array',
            tickvals: tickVals,
            ticktext: tickText,
            gridcolor: '#d1d5db',
            zeroline: false,
            showgrid: true,
            domain: [bottom, top],
            anchor: xAxisKey,
        };
        axesDict[`xaxis${row}`] = {
            title: idx === bars.length - 1 ? 'Time (s)' : '',
            zeroline: false,
            gridcolor: '#e5e7eb',
            showticklabels: idx === bars.length - 1,
            ticksuffix: 's',
            anchor: yAxisKey,
        };
    });
    axesDict.xaxis = { ...axesDict.xaxis1 };
    axesDict.yaxis = { ...axesDict.yaxis1 };
    delete axesDict.xaxis1;
    delete axesDict.yaxis1;
    const layout = {
        title: { text: 'Musical Score', font: { size: 14 } },
        paper_bgcolor: 'white',
        plot_bgcolor: '#fafafa',
        margin: { l: 60, r: 20, t: 50, b: 60 },
        ...axesDict,
        showlegend: false,
        uniformtext: { mode: 'hide', minsize: 8 },
    };
    return { traces, layout };
}

class ProsodyLabRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.startTime = null;
        this.timerInterval = null;
        this.recordingTimeout = null;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        this.maxDuration = 30;
        this.historyStorage = window.__SPEECH_GUIDER_DESKTOP__
            ? createDesktopHistoryStorage(window.__DESKTOP_HISTORY__)
            : undefined;
        this.locked = false;
        this.beatsPerBar = 4;
        this.zoomLevel = 1.0;
        this.phraseId = 'prepared';
        this.profileKey = 'dysfluent_hesitation';
        this.dtwNormFactor = 1.0;
        this.activeRhythmTab = 'review';
        this.audioMode = 'synth_beats';
        this.performer = 'bot_native';
        this.flowPlaying = false;
        this.flowStartMs = 0;
        this.flowBeat = 0.0;
        this.flowResponseBar = false;
        this.flowAnimationId = null;
        this.playheadRafId = null;
        this.audioPlayer = new ProsodyAudioPlayer();
        this.latestRecordedBlobUrl = null;
        this.referenceTtsCache = {};
        this.stream = null;
        this.visualizerSource = null;
        this.eventListeners = [];
        this.eventsBound = false;
        this.destroyed = false;
        this.initPromise = null;
        this.permissionRequestId = 0;
        this.isStartingRecording = false;
        this.cancelOnStop = false;

        this.initElements();
        this.bindEvents();
        this.renderRhythmViews(this.loadHistory());
    }

    initElements() {
        this.recordBtn = document.getElementById('prosody-record-btn');
        this.recTimer = document.getElementById('prosody-rec-timer');
        this.waveformCanvas = document.getElementById('prosody-waveform');
        this.statusEl = document.getElementById('prosody-status');
        this.feedbackEl = document.getElementById('prosody-feedback');
        this.historyEl = document.getElementById('prosody-history');
        this.currentSummaryEl = document.getElementById('prosody-current-summary');
        this.currentLabelEl = document.getElementById('prosody-current-label');
        this.currentPlotEl = document.getElementById('prosody-current-plot');
        this.teacherLabelEl = document.getElementById('prosody-teacher-label');
        this.studentLabelEl = document.getElementById('prosody-student-label');
        this.teacherPlotEl = document.getElementById('prosody-teacher-plot');
        this.studentPlotEl = document.getElementById('prosody-student-plot');
        this.tetherStageEl = document.getElementById('prosody-tether-stage');
        this.flowStageEl = document.getElementById('prosody-flow-stage');
        this.reviewTabBtnEl = document.getElementById('prosody-view-tab-review');
        this.liveTabBtnEl = document.getElementById('prosody-view-tab-live');
        this.reviewPanelEl = document.getElementById('prosody-panel-review');
        this.livePanelEl = document.getElementById('prosody-panel-live');
        this.phraseSelectEl = document.getElementById('prosody-phrase-select');
        this.audioModeSelectEl = document.getElementById('prosody-audio-mode-select');
        this.customTextEl = document.getElementById('prosody-custom-text');
        this.customGenerateBtnEl = document.getElementById('prosody-custom-generate-btn');
        this.profileSelectEl = document.getElementById('prosody-profile-select');
        this.playRefBtnEl = document.getElementById('prosody-play-ref-btn');
        this.playLearnerBtnEl = document.getElementById('prosody-play-learner-btn');
        this.stopAudioBtnEl = document.getElementById('prosody-stop-audio-btn');
        this.performerSelectEl = document.getElementById('prosody-performer-select');
        this.flowPlayBtnEl = document.getElementById('prosody-flow-play-btn');
        this.flowBar2BtnEl = document.getElementById('prosody-flow-bar2-btn');
        this.sendToReviewBtnEl = document.getElementById('prosody-send-to-review-btn');

        if (this.waveformCanvas) {
            this.canvas = this.waveformCanvas;
            this.canvasCtx = this.canvas.getContext('2d');
        }
    }

    bindEvents() {
        if (this.eventsBound || this.destroyed) return;
        this.eventsBound = true;
        listen(this, window, 'beforeunload', () => this.destroy());

        // F5 key listener (disabled in Tauri mode - Tauri uses Tab instead)
        if (!window.__SPEECH_GUIDER_TAURI__ && !window.__TAURI__) {
            listen(this, document, 'keydown', (event) => {
                if (event.key === 'F5' && window.currentTab === 'prosody') {
                    event.preventDefault();
                    if (!this.isRecording) {
                        this.startRecording();
                    }
                }
            });

            listen(this, document, 'keyup', (event) => {
                if (event.key === 'F5' && window.currentTab === 'prosody' && this.isRecording) {
                    event.preventDefault();
                    this.stopRecording();
                }
            });
        }

        if (this.recordBtn) {
            listen(this, this.recordBtn, 'mousedown', () => this.startRecording());
            listen(this, this.recordBtn, 'mouseup', () => this.stopRecording());
            listen(this, this.recordBtn, 'mouseleave', () => {
                if (this.isRecording) this.stopRecording();
            });
            listen(this, this.recordBtn, 'touchstart', (event) => {
                event.preventDefault();
                this.startRecording();
            });
            listen(this, this.recordBtn, 'touchend', (event) => {
                event.preventDefault();
                this.stopRecording();
            });
        }

        if (this.reviewTabBtnEl) {
            listen(this, this.reviewTabBtnEl, 'click', () => {
                this.setRhythmTab('review');
            });
        }
        if (this.liveTabBtnEl) {
            listen(this, this.liveTabBtnEl, 'click', () => {
                this.setRhythmTab('live');
            });
        }
        if (this.phraseSelectEl) {
            listen(this, this.phraseSelectEl, 'change', () => {
                this.phraseId = this.phraseSelectEl.value || 'prepared';
                const phrase = getPhraseById(this.phraseId);
                if (this.customTextEl && this.phraseId !== 'custom') {
                    this.customTextEl.value = phrase.title.replace(/\.\.\./g, ',').replace(/-/g, '');
                }
                this.renderRhythmViews(this.loadHistory());
            });
        }
        if (this.audioModeSelectEl) {
            listen(this, this.audioModeSelectEl, 'change', () => {
                this.audioMode = this.audioModeSelectEl.value || 'synth_beats';
            });
        }
        if (this.customGenerateBtnEl) {
            listen(this, this.customGenerateBtnEl, 'click', () => {
                void this.generateCustomSentenceReference();
            });
        }
        if (this.profileSelectEl) {
            listen(this, this.profileSelectEl, 'change', () => {
                this.profileKey = this.profileSelectEl.value || 'dysfluent_hesitation';
                this.renderRhythmViews(this.loadHistory());
            });
        }
        if (this.playRefBtnEl) {
            listen(this, this.playRefBtnEl, 'click', () => {
                void this.auditionTimingTrack('reference');
            });
        }
        if (this.playLearnerBtnEl) {
            listen(this, this.playLearnerBtnEl, 'click', () => {
                void this.auditionTimingTrack('learner');
            });
        }
        if (this.stopAudioBtnEl) {
            listen(this, this.stopAudioBtnEl, 'click', () => {
                this.stopAllAudio();
            });
        }
        if (this.performerSelectEl) {
            listen(this, this.performerSelectEl, 'change', () => {
                this.performer = this.performerSelectEl.value || 'bot_native';
                this.renderRhythmViews(this.loadHistory());
            });
        }
        if (this.flowPlayBtnEl) {
            listen(this, this.flowPlayBtnEl, 'click', () => {
                this.toggleFlowLoop();
            });
        }
        if (this.flowBar2BtnEl) {
            listen(this, this.flowBar2BtnEl, 'click', () => {
                this.flowResponseBar = true;
                this.flowBeat = 2.0;
                this.renderFlowMatrixStage(this.loadHistory());
            });
        }
        if (this.sendToReviewBtnEl) {
            listen(this, this.sendToReviewBtnEl, 'click', () => {
                if (this.performer === 'bot_native') {
                    this.profileKey = 'native_expressive';
                } else if (this.performer === 'bot_choppy') {
                    this.profileKey = 'syllable_timed_choppy';
                } else if (this.performer === 'bot_dysfluent') {
                    this.profileKey = 'dysfluent_hesitation';
                } else {
                    this.profileKey = 'recorded_take';
                }
                if (this.profileSelectEl) {
                    this.profileSelectEl.value = this.profileKey;
                }
                this.setRhythmTab('review');
                this.renderRhythmViews(this.loadHistory());
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
        if (!navigator.mediaDevices?.getUserMedia) {
            this.setStatus('Microphone recording is not supported in this browser.', true);
            this.initPromise = null;
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
            this.setStatus('Ready to record a short sample.');
            this.renderFromStorage();
        } catch (error) {
            this.isStartingRecording = false;
            if (this.destroyed || requestId !== this.permissionRequestId) return;
            releaseCapture(this);
            this.mediaRecorder = null;
            this.setStatus(microphoneError(error), true);
        } finally {
            if (!this.destroyed) this.initPromise = null;
        }
    }

    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        this.permissionRequestId += 1;
        this.isStartingRecording = false;
        this.cancelOnStop = true;
        this.isRecording = false;
        this.stopAllAudio();
        this.stopFlowLoop();
        if (this.latestRecordedBlobUrl && typeof URL?.revokeObjectURL === 'function') {
            URL.revokeObjectURL(this.latestRecordedBlobUrl);
            this.latestRecordedBlobUrl = null;
        }
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

    setupRecorder(stream) {
        this.stream = stream;
        this.mediaRecorder = new MediaRecorder(stream);
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        };
        this.mediaRecorder.onstop = () => {
            if (!this.cancelOnStop && !this.destroyed) this.sendForAnalysis();
        };
    }

    setupVisualizer(stream) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
        const source = this.audioContext.createMediaStreamSource(stream);
        this.visualizerSource = source;
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    }

    setStatus(message, isError = false) {
        if (!this.statusEl) return;
        this.statusEl.textContent = message;
        this.statusEl.className = `text-xs ${isError ? 'text-red-600' : 'text-gray-600'}`;
    }

    startRecording() {
        if (this.destroyed || this.isStartingRecording || this.isRecording || !this.mediaRecorder || window.currentTab !== 'prosody') return;

        this.stopAllAudio();
        this.isRecording = true;
        this.audioChunks = [];
        this.startTime = Date.now();
        this.setStatus('Recording... release to analyze.');

        if (this.recordBtn) {
            this.recordBtn.classList.add('recording');
            const btnText = this.recordBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Recording...';
        }
        this.mediaRecorder.start(100);
        this.drawWaveform();

        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            if (this.recTimer) {
                this.recTimer.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
            }
        }, 100);

        this.recordingTimeout = setTimeout(() => {
            if (this.isRecording) {
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
            if (btnText) btnText.textContent = 'Hold to Record';
        }

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.setStatus('Analyzing recording...');
            this.mediaRecorder.stop();
        }
    }

    drawWaveform() {
        if (!this.isRecording || !this.analyser || !this.canvas || !this.canvasCtx || !this.dataArray) return;

        this.animationId = requestAnimationFrame(() => this.drawWaveform());
        this.analyser.getByteTimeDomainData(this.dataArray);

        this.canvasCtx.fillStyle = 'rgb(240, 240, 240)';
        this.canvasCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.strokeStyle = 'rgb(16, 185, 129)';
        this.canvasCtx.beginPath();

        const sliceWidth = this.canvas.width / this.dataArray.length;
        let x = 0;
        for (let index = 0; index < this.dataArray.length; index += 1) {
            const y = (this.dataArray[index] / 128.0) * (this.canvas.height / 2);
            if (index === 0) {
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
        if (!this.audioChunks.length) {
            this.setStatus('No audio recorded.', true);
            return;
        }

        try {
            const wavBlob = await this.convertToWav(new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || this.audioChunks[0]?.type }));
            if (this.destroyed) return;
            if (this.latestRecordedBlobUrl && typeof URL?.revokeObjectURL === 'function') {
                URL.revokeObjectURL(this.latestRecordedBlobUrl);
            }
            if (typeof URL?.createObjectURL === 'function') {
                this.latestRecordedBlobUrl = URL.createObjectURL(wavBlob);
            }

            const formData = new FormData();
            formData.append('audio', wavBlob, 'prosody-recording.wav');

            const response = await fetch('/api/prosody-lab/analyze', { method: 'POST', body: formData });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            if (this.destroyed) return;
            this.profileKey = 'recorded_take';
            if (this.profileSelectEl) {
                this.profileSelectEl.value = 'recorded_take';
            }
            await this.storeRecord(result);
            this.renderFromStorage(result.recording_id);
            this.setStatus('Analysis complete.');
        } catch (error) {
            console.error('Prosody Lab analysis failed:', error);
            this.setStatus(`Analysis failed: ${error.message}`, true);
        } finally {
            if (this.recTimer) {
                this.recTimer.textContent = '00:00';
            }
        }
    }

    async generateCustomSentenceReference() {
        const rawText = (this.customTextEl?.value || '').trim();
        if (!rawText) {
            this.setStatus('Enter a custom sentence first.', true);
            return;
        }
        if (this.customGenerateBtnEl) {
            this.customGenerateBtnEl.disabled = true;
            this.customGenerateBtnEl.textContent = 'Generating...';
        }
        this.setStatus('Synthesizing reference & P-centers...');
        try {
            const response = await fetch('/api/prosody-lab/reference', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_text: rawText }),
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            if (this.destroyed) return;
            setCustomPhrase({
                ...data.phrase,
                audioBase64: data.audio_base64,
                mimeType: data.mime_type || 'audio/wav',
            });
            this.referenceTtsCache.custom = {
                audioBase64: data.audio_base64,
                mimeType: data.mime_type || 'audio/wav',
            };
            this.phraseId = 'custom';
            if (this.phraseSelectEl) {
                this.phraseSelectEl.value = 'custom';
            }
            this.renderRhythmViews(this.loadHistory());
            this.setStatus(`Reference ready (${data.phrase?.syllables?.length || 0} syllables).`);
        } catch (error) {
            console.error('Custom reference synthesis failed:', error);
            this.setStatus(`Reference failed: ${error.message}`, true);
        } finally {
            if (this.customGenerateBtnEl) {
                this.customGenerateBtnEl.disabled = false;
                this.customGenerateBtnEl.textContent = 'Generate Reference (TTS)';
            }
        }
    }

    async auditionTimingTrack(which = 'reference') {
        this.stopAllAudio();
        const history = this.loadHistory();
        const teacherRecord = history.find((item) => item.recording_id === this.getTeacherId()) || history[1] || null;
        const studentRecord = history.find((item) => item.recording_id === this.getStudentId()) || history[0] || null;
        const aligned = alignRecordPairToTetherItems(teacherRecord, studentRecord, this.phraseId, this.profileKey);
        const phrase = aligned.phrase;
        const bpm = phrase.bpm || 88;
        const durationMs = Math.round((60 / bpm) * 4.4 * 1000);

        if (this.audioMode === 'real_tts') {
            if (which === 'learner' && this.latestRecordedBlobUrl) {
                this.audioPlayer.playBlobUrl(this.latestRecordedBlobUrl);
            } else if (which === 'reference') {
                let tts = phrase.audioBase64
                    ? { audioBase64: phrase.audioBase64, mimeType: phrase.mimeType || 'audio/wav' }
                    : this.referenceTtsCache[this.phraseId];
                if (!tts) {
                    try {
                        const cleanSentence = phrase.title.replace(/\.\.\./g, ',').replace(/-/g, '');
                        const resp = await fetch('/api/prosody-lab/reference', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ target_text: cleanSentence }),
                        });
                        if (resp.ok) {
                            const payload = await resp.json();
                            tts = { audioBase64: payload.audio_base64, mimeType: payload.mime_type || 'audio/wav' };
                            this.referenceTtsCache[this.phraseId] = tts;
                        }
                    } catch {
                        // Fall back to clean formant voice without beats
                    }
                }
                if (tts?.audioBase64) {
                    this.audioPlayer.playBase64Audio(tts.audioBase64, tts.mimeType);
                } else {
                    this.audioPlayer.playSyllableSequence(aligned.natSyls, bpm, false);
                }
            } else {
                this.audioPlayer.playSyllableSequence(aligned.lrnSyls, bpm, false);
            }
        } else {
            const syls = which === 'reference' ? aligned.natSyls : aligned.lrnSyls;
            this.audioPlayer.playSyllableSequence(syls, bpm, true);
        }

        this.startTetherPlayheadSweep(durationMs);
    }

    startTetherPlayheadSweep(durationMs) {
        if (this.playheadRafId) {
            cancelAnimationFrame(this.playheadRafId);
            this.playheadRafId = null;
        }
        const playheadEl = document.getElementById('prosody-tether-playhead');
        if (!playheadEl) return;

        playheadEl.style.opacity = '1';
        const startMs = performance.now();
        const step = (now) => {
            const frac = Math.min(1, Math.max(0, (now - startMs) / Math.max(400, durationMs)));
            const x = 48 + frac * (928 - 48);
            playheadEl.setAttribute('transform', `translate(${x.toFixed(1)}, 0)`);
            if (frac < 1 && !this.destroyed) {
                this.playheadRafId = requestAnimationFrame(step);
            } else {
                playheadEl.style.opacity = '0';
                this.playheadRafId = null;
            }
        };
        this.playheadRafId = requestAnimationFrame(step);
    }

    stopAllAudio() {
        this.audioPlayer.stop();
        if (this.playheadRafId) {
            cancelAnimationFrame(this.playheadRafId);
            this.playheadRafId = null;
        }
        const playheadEl = document.getElementById('prosody-tether-playhead');
        if (playheadEl) {
            playheadEl.style.opacity = '0';
        }
    }

    async convertToWav(audioBlob) {
        return convertAudioToWav(audioBlob, 44100, (buffer, length) => this.bufferToWave(buffer, length));
    }

    bufferToWave(buffer, length) {
        return encodePcmWav(buffer, length);
    }

    async storeRecord(record) {
        storeRecord(record, this.historyStorage);
        await this.historyStorage?.flush();
    }

    loadHistory() {
        return loadHistory(this.historyStorage);
    }

    getTeacherId() {
        return getRoleId('teacher', this.historyStorage);
    }

    getStudentId() {
        return getRoleId('student', this.historyStorage);
    }

    async setRole(role, recordingId) {
        try {
            setRoleId(role, recordingId, this.historyStorage);
            this.renderFromStorage();
            await this.historyStorage?.flush();
        } catch (error) {
            this.setStatus(error.message, true);
        }
    }

    renderFromStorage(currentId = '') {
        const history = this.loadHistory();
        const currentRecord = currentId ? history.find((item) => item.recording_id === currentId) : history[0];
        if (currentRecord) {
            this.renderCurrent(currentRecord);
        }
        this.renderHistory(history);
        this.renderComparison(history);
        this.renderRhythmViews(history);
    }

    renderCurrent(record) {
        if (this.currentLabelEl) {
            this.currentLabelEl.textContent = record.recording_id ? `Recording ${record.recording_id.slice(0, 6)}` : 'Latest recording';
        }

        if (this.currentSummaryEl) {
            const summary = record.summary || {};
            this.currentSummaryEl.innerHTML = [
                ['Syllables', summary.syllable_count],
                ['Pauses', summary.pause_count],
                ['Rhythm balance', formatMetricValue(summary.rhythm_balance)],
                ['Mean note', summary.mean_note],
                ['Mean F0', formatMetricValue(summary.mean_f0_hz, ' Hz')],
                ['Rate', formatMetricValue(summary.speech_rate, ' syll/s')],
            ]
                .map(([label, value]) => `
          <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
            <div class="text-xs uppercase tracking-wide text-gray-500">${escapeHtml(label)}</div>
            <div class="text-sm font-semibold text-gray-800">${escapeHtml(value === undefined || value === null ? '—' : value)}</div>
          </div>`)
                .join('');
        }

        this.renderPlot(this.currentPlotEl, record);
        this.renderFeedback(record);
    }

    renderFeedback(record) {
        if (!this.feedbackEl) return;

        const summary = record.summary || {};
        const phrase = getPhraseById(this.phraseId);
        this.feedbackEl.innerHTML = `
      <p><strong>Phrase focus:</strong> ${escapeHtml(phrase.teacherNote || phrase.title)}</p>
      <p><strong>Syllables:</strong> ${escapeHtml(summary.syllable_count ?? '—')} acoustic P-center nuclei</p>
      <p><strong>Pauses:</strong> ${escapeHtml(summary.pause_count ?? '—')} detected spans</p>
      <p><strong>Rhythm balance:</strong> ${escapeHtml(formatMetricValue(summary.rhythm_balance))}</p>
      <p><strong>Speaking rate:</strong> ${escapeHtml(formatMetricValue(summary.speech_rate, ' syll/s'))} (Articulation: ${escapeHtml(formatMetricValue(summary.articulation_rate, ' syll/s'))})</p>
      <p><strong>Mean speaking note:</strong> ${escapeHtml(summary.mean_note ?? '—')} (${escapeHtml(formatMetricValue(summary.mean_f0_hz, ' Hz'))})</p>
    `;
    }

    renderHistory(history) {
        if (!this.historyEl) return;

        if (history.length === 0) {
            this.historyEl.innerHTML = '<p class="text-sm text-gray-500">No recordings yet.</p>';
            return;
        }

        const teacherId = this.getTeacherId();
        const studentId = this.getStudentId();

        this.historyEl.innerHTML = history
            .map((record) => {
                const isTeacher = record.recording_id === teacherId;
                const isStudent = record.recording_id === studentId;
                const createdAt = record.created_at ? new Date(record.created_at).toLocaleTimeString() : 'Just now';
                const recordingId = escapeHtml(record.recording_id || '');
                return `
          <div class="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="font-medium text-gray-800">Recording ${escapeHtml(String(record.recording_id || '').slice(0, 6))}</div>
                <div class="text-xs text-gray-500">${escapeHtml(createdAt)}</div>
                <div class="mt-2 text-sm text-gray-700">
                  <span class="mr-3">Syllables: ${escapeHtml(record.summary?.syllable_count ?? '—')}</span>
                  <span class="mr-3">Pauses: ${escapeHtml(record.summary?.pause_count ?? '—')}</span>
                  <span>Balance: ${escapeHtml(formatMetricValue(record.summary?.rhythm_balance))}</span>
                </div>
              </div>
              <div class="flex flex-col gap-2 text-xs">
                <button type="button" class="rounded bg-blue-600 px-3 py-1 font-medium text-white hover:bg-blue-700" data-role="teacher" data-recording-id="${recordingId}">
                  ${isTeacher ? 'Teacher sample' : 'Set as teacher'}
                </button>
                <button type="button" class="rounded bg-emerald-600 px-3 py-1 font-medium text-white hover:bg-emerald-700" data-role="student" data-recording-id="${recordingId}">
                  ${isStudent ? 'Student sample' : 'Set as student'}
                </button>
              </div>
            </div>
          </div>`;
            })
            .join('');

        this.historyEl.querySelectorAll('button[data-role]').forEach((button) => {
            button.addEventListener('click', () => {
                this.setRole(button.getAttribute('data-role') || '', button.getAttribute('data-recording-id') || '');
            });
        });
    }

    renderComparison(history) {
        const teacherRecord = history.find((item) => item.recording_id === this.getTeacherId()) || history[1] || null;
        const studentRecord = history.find((item) => item.recording_id === this.getStudentId()) || history[0] || null;

        if (this.teacherLabelEl) {
            this.teacherLabelEl.textContent = teacherRecord ? `Recording ${teacherRecord.recording_id.slice(0, 6)}` : 'None selected';
        }
        if (this.studentLabelEl) {
            this.studentLabelEl.textContent = studentRecord ? `Recording ${studentRecord.recording_id.slice(0, 6)}` : 'None selected';
        }

        this.renderPlot(this.teacherPlotEl, teacherRecord);
        this.renderPlot(this.studentPlotEl, studentRecord);
    }

    setRhythmTab(tab) {
        this.activeRhythmTab = tab === 'live' ? 'live' : 'review';
        const isReview = this.activeRhythmTab === 'review';
        if (this.reviewPanelEl) this.reviewPanelEl.classList.toggle('hidden', !isReview);
        if (this.livePanelEl) this.livePanelEl.classList.toggle('hidden', isReview);
        if (this.reviewTabBtnEl) {
            this.reviewTabBtnEl.className = isReview
                ? 'rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm'
                : 'rounded-md bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200';
        }
        if (this.liveTabBtnEl) {
            this.liveTabBtnEl.className = !isReview
                ? 'rounded-md bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm'
                : 'rounded-md bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200';
        }
        if (isReview && this.flowPlaying) {
            this.stopFlowLoop();
        }
    }

    renderRhythmViews(history = []) {
        const teacherRecord = history.find((item) => item.recording_id === this.getTeacherId()) || history[1] || null;
        const studentRecord = history.find((item) => item.recording_id === this.getStudentId()) || history[0] || null;

        if (this.tetherStageEl) {
            this.tetherStageEl.innerHTML = renderVocAlignTetherDiagnosticSVG({
                phraseId: this.phraseId,
                profileKey: this.profileKey,
                normFactor: this.dtwNormFactor,
                teacherRecord,
                studentRecord,
            });
        }
        this.renderFlowMatrixStage(history);
    }

    renderFlowMatrixStage(history = []) {
        if (!this.flowStageEl) return;
        const studentRecord = history.find((item) => item.recording_id === this.getStudentId()) || history[0] || null;
        this.flowStageEl.innerHTML = renderFlowMatrixTrainerSVG({
            phraseId: this.phraseId,
            beat: this.flowBeat,
            isResponseBar: this.flowResponseBar,
            performer: this.performer,
            liveRecord: studentRecord,
        });
    }

    toggleFlowLoop() {
        if (this.flowPlaying) {
            this.stopFlowLoop();
        } else {
            this.startFlowLoop();
        }
    }

    startFlowLoop() {
        if (this.flowPlaying || this.destroyed) return;
        this.stopAllAudio();
        this.flowPlaying = true;
        this.flowStartMs = performance.now();
        this.lastLoopBarIndex = -1;
        if (this.flowPlayBtnEl) {
            this.flowPlayBtnEl.textContent = '■ Stop 2-Bar Loop';
        }
        const phrase = getPhraseById(this.phraseId);
        const bpm = phrase.bpm || 88;
        const beatDurMs = (60 / bpm) * 1000;

        const step = (now) => {
            if (!this.flowPlaying || this.destroyed) return;
            const totalBeats = (now - this.flowStartMs) / beatDurMs;
            const barIdx = Math.floor(totalBeats / 4.0);
            const elapsedBeats = totalBeats % 8.0;
            this.flowResponseBar = elapsedBeats >= 4.0;
            this.flowBeat = elapsedBeats % 4.0;

            if (barIdx !== this.lastLoopBarIndex) {
                this.lastLoopBarIndex = barIdx;
                const includeBeats = this.audioMode === 'synth_beats';
                if (!this.flowResponseBar) {
                    this.audioPlayer.playSyllableSequence(phrase.syllables, bpm, includeBeats);
                } else if (includeBeats) {
                    for (let b = 0; b < 4; b += 1) {
                        const ctx = this.audioPlayer._ensureCtx();
                        if (ctx) {
                            this.audioPlayer.scheduleBeatClick(b, ctx.currentTime + 0.02 + b * (60 / bpm));
                        }
                    }
                }
            }

            this.renderFlowMatrixStage(this.loadHistory());
            this.flowAnimationId = requestAnimationFrame(step);
        };
        this.flowAnimationId = requestAnimationFrame(step);
    }

    stopFlowLoop() {
        this.flowPlaying = false;
        if (this.flowAnimationId) {
            cancelAnimationFrame(this.flowAnimationId);
            this.flowAnimationId = null;
        }
        this.audioPlayer.stop();
        if (this.flowPlayBtnEl) {
            this.flowPlayBtnEl.textContent = '▶ Start 2-Bar Loop';
        }
    }

    renderPlot(targetElement, record) {
        if (!targetElement) return;
        if (!record || !window.Plotly) {
            targetElement.innerHTML = '<div class="text-sm text-gray-500">No recording selected.</div>';
            return;
        }

        const beatsSel = document.getElementById('prosody-beats-select');
        const effectiveBeats = (beatsSel && beatsSel.value !== 'auto')
            ? parseInt(beatsSel.value, 10)
            : detectBeatsPerBar(record.summary?.syllable_count || 0, record.summary?.duration_seconds || 0);

        const chartData = buildMusicalScoreChart(record, {
            locked: this.locked,
            beatsPerBar: effectiveBeats,
            zoomLevel: this.zoomLevel,
        });
        if (!chartData.traces.length) {
            targetElement.innerHTML = '<div class="text-sm text-gray-500">No pitch data available.</div>';
            return;
        }
        const config = { responsive: true, displayModeBar: true, displaylogo: false, scrollZoom: true };
        window.Plotly.newPlot(targetElement, chartData.traces, chartData.layout, config);
    }
}

function initializeProsodyLab() {
    const recordBtn = document.getElementById('prosody-record-btn');
    const recorderContainer = document.getElementById('prosody-recorder');
    if (!recordBtn || !recorderContainer) return;

    window.prosodyLabRecorder?.destroy?.();
    window.prosodyLabRecorder = new ProsodyLabRecorder();
    const recorder = window.prosodyLabRecorder;

    const lockBtn = document.getElementById('prosody-lock-btn');
    const beatsSelect = document.getElementById('prosody-beats-select');
    const zoomSlider = document.getElementById('prosody-zoom-slider');
    const zoomLabel = document.getElementById('prosody-zoom-label');

    if (lockBtn) {
        listen(recorder, lockBtn, 'click', () => {
            if (!window.prosodyLabRecorder) return;
            window.prosodyLabRecorder.locked = !window.prosodyLabRecorder.locked;
            lockBtn.classList.toggle('bg-blue-600', window.prosodyLabRecorder.locked);
            lockBtn.classList.toggle('text-white', window.prosodyLabRecorder.locked);
            lockBtn.classList.toggle('bg-white', !window.prosodyLabRecorder.locked);
            window.prosodyLabRecorder.renderFromStorage();
        });
    }

    if (beatsSelect) {
        listen(recorder, beatsSelect, 'change', () => {
            if (!window.prosodyLabRecorder) return;
            const val = beatsSelect.value;
            if (val !== 'auto') {
                window.prosodyLabRecorder.beatsPerBar = parseInt(val, 10);
            }
            window.prosodyLabRecorder.renderFromStorage();
        });
    }

    if (zoomSlider && zoomLabel) {
        listen(recorder, zoomSlider, 'input', () => {
            if (!window.prosodyLabRecorder) return;
            window.prosodyLabRecorder.zoomLevel = parseFloat(zoomSlider.value);
            zoomLabel.textContent = `${window.prosodyLabRecorder.zoomLevel.toFixed(2)}x`;
            window.prosodyLabRecorder.renderFromStorage();
        });
    }
}

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeProsodyLab);
    } else {
        initializeProsodyLab();
    }
}

if (typeof window !== 'undefined') {
    window.ProsodyLabRecorder = ProsodyLabRecorder;
    window.trimProsodyHistory = trimProsodyHistory;
    window.midiToNoteName = midiToNoteName;
}

export { ProsodyLabRecorder, trimProsodyHistory, midiToNoteName, buildMusicalScoreChart };
