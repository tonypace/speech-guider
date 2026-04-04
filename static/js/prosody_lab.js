const PROSODY_HISTORY_KEY = 'prosodyLabHistory';
const PROSODY_TEACHER_KEY = 'prosodyLabTeacherId';
const PROSODY_STUDENT_KEY = 'prosodyLabStudentId';
const MAX_HISTORY_ITEMS = 3;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

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

function trimProsodyHistory(history, maxItems = MAX_HISTORY_ITEMS) {
  return history.slice(0, maxItems);
}

function safeParseJson(rawValue, fallback) {
  try {
    const parsed = JSON.parse(rawValue);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
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
  for (let midi = Math.floor(minMidi); midi <= Math.ceil(maxMidi); midi += 1) {
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

function classifySyllableStress(syllableOnsets, pitchTrack) {
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

function buildBarTrace(bar, quantizedMidi, localTimes, textValues, anchorTimes, graceTimes, rowMidiRange) {
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
  const syllableOnsets = record?.syllable_onsets || [];
  const summary = record?.summary || {};
  const barDuration = BAR_DURATION_SECONDS / zoomLevel;
  const bars = chunkIntoBars(pitchTrack, barDuration);

  if (bars.length === 0) {
    return { traces: [], layout: {}, frames: [] };
  }
  const { stressed, unstressed } = classifySyllableStress(syllableOnsets, pitchTrack);
  const graceTimes = assignGraceNotesBetween(unstressed, stressed);
  const allMidi = pitchTrack.map((p) => p.midi).filter((m) => m !== null && !Number.isNaN(m));
  const globalMinMidi = allMidi.length ? Math.floor(Math.min(...allMidi)) - 1 : 36;
  const globalMaxMidi = allMidi.length ? Math.ceil(Math.max(...allMidi)) + 1 : 72;
  const { tickVals, tickText } = buildNoteTicks(globalMinMidi, globalMaxMidi);
  const beatInterval = barDuration / beatsPerBar;
  const traces = [];
  const annotations = [];
  const shapes = [];

  bars.forEach((bar, idx) => {
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
    const barTraces = buildBarTrace(bar, quantizedMidi, localTimes, textValues, anchorTimes, barGraceTimes, [globalMinMidi, globalMaxMidi]);
    traces.push(...barTraces);
  });
  const axesDict = {};
  bars.forEach((bar, idx) => {
    const row = idx + 1;
    axesDict[`yaxis${row}`] = {
      title: idx === 0 ? 'Note' : '',
      range: [globalMinMidi, globalMaxMidi],
      tickmode: 'array',
      tickvals: tickVals,
      ticktext: tickText,
      gridcolor: '#d1d5db',
      zeroline: false,
      showgrid: true,
      domain: [1 - row / bars.length, 1 - (row - 1) / bars.length],
    };
    axesDict[`xaxis${row}`] = {
      title: idx === bars.length - 1 ? 'Time (s)' : '',
      zeroline: false,
      gridcolor: '#e5e7eb',
      showticklabels: true,
      ticksuffix: 's',
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
    annotations,
    shapes,
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
    this.locked = false;
    this.beatsPerBar = 4;
    this.zoomLevel = 1.0;

    this.initElements();
    this.bindEvents();
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

    if (this.waveformCanvas) {
      this.canvas = this.waveformCanvas;
      this.canvasCtx = this.canvas.getContext('2d');
    }
  }

  bindEvents() {
    // F5 key listener (disabled in Tauri mode - Tauri uses Tab instead)
    if (!window.__TAURI__) {
      document.addEventListener('keydown', (event) => {
        if (event.key === 'F5' && window.currentTab === 'prosody') {
          event.preventDefault();
          if (!this.isRecording) {
            this.startRecording();
          }
        }
      });

      document.addEventListener('keyup', (event) => {
        if (event.key === 'F5' && window.currentTab === 'prosody' && this.isRecording) {
          event.preventDefault();
          this.stopRecording();
        }
      });
    }

    if (this.recordBtn) {
      this.recordBtn.addEventListener('mousedown', () => this.startRecording());
      this.recordBtn.addEventListener('mouseup', () => this.stopRecording());
      this.recordBtn.addEventListener('mouseleave', () => {
        if (this.isRecording) this.stopRecording();
      });
      this.recordBtn.addEventListener('touchstart', (event) => {
        event.preventDefault();
        this.startRecording();
      });
      this.recordBtn.addEventListener('touchend', (event) => {
        event.preventDefault();
        this.stopRecording();
      });
    }
  }

  async init() {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.setStatus('Microphone recording is not supported in this browser.', true);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.setupRecorder(stream);
      this.setupVisualizer(stream);
      this.setStatus('Ready to record a short sample.');
      this.renderFromStorage();
    } catch (error) {
      this.setStatus(`Microphone access failed: ${error.message}`, true);
    }
  }

  setupRecorder(stream) {
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };
    this.mediaRecorder.onstop = () => this.sendForAnalysis();
  }

  setupVisualizer(stream) {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
    const source = this.audioContext.createMediaStreamSource(stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    source.connect(this.analyser);
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
  }

  setStatus(message, isError = false) {
    if (!this.statusEl) return;
    this.statusEl.textContent = message;
    this.statusEl.className = `mt-4 text-sm ${isError ? 'text-red-600' : 'text-gray-600'}`;
  }

  startRecording() {
    if (this.isRecording || !this.mediaRecorder || window.currentTab !== 'prosody') return;

    this.isRecording = true;
    this.audioChunks = [];
    this.startTime = Date.now();
    this.setStatus('Recording... release to analyze.');

    this.recordBtn?.classList.add('recording');
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
    if (!this.isRecording) return;

    this.isRecording = false;
    clearInterval(this.timerInterval);
    clearTimeout(this.recordingTimeout);
    this.recordBtn?.classList.remove('recording');

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
      const wavBlob = await this.convertToWav(new Blob(this.audioChunks, { type: 'audio/webm' }));
      const formData = new FormData();
      formData.append('audio', wavBlob, 'prosody-recording.wav');

      const response = await fetch('/api/prosody-lab/analyze', { method: 'POST', body: formData });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      this.storeRecord(result);
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

  async convertToWav(audioBlob) {
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const wavBlob = this.bufferToWave(audioBuffer, audioBuffer.length);
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

    setUint32(0x46464952);
    setUint32(length - 8);
    setUint32(0x45564157);
    setUint32(0x20746d66);
    setUint32(16);
    setUint16(1);
    setUint16(numOfChan);
    setUint32(abuffer.sampleRate);
    setUint32(abuffer.sampleRate * 2 * numOfChan);
    setUint16(numOfChan * 2);
    setUint16(16);
    setUint32(0x61746164);
    setUint32(length - pos - 4);

    for (let channelIndex = 0; channelIndex < abuffer.numberOfChannels; channelIndex += 1) {
      channels.push(abuffer.getChannelData(channelIndex));
    }

    while (pos < length) {
      for (let channelIndex = 0; channelIndex < numOfChan; channelIndex += 1) {
        let sample = clamp(channels[channelIndex][offset] || 0, -1, 1);
        sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
        view.setInt16(pos, sample, true);
        pos += 2;
      }
      offset += 1;
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

  storeRecord(record) {
    const storedRecord = {
      ...record,
      created_at: new Date().toISOString(),
    };
    const history = this.loadHistory();
    const nextHistory = trimProsodyHistory([
      storedRecord,
      ...history.filter((item) => item.recording_id !== storedRecord.recording_id),
    ]);
    localStorage.setItem(PROSODY_HISTORY_KEY, JSON.stringify(nextHistory));

    const teacherId = localStorage.getItem(PROSODY_TEACHER_KEY);
    const studentId = localStorage.getItem(PROSODY_STUDENT_KEY);
    const hasTeacher = nextHistory.some((item) => item.recording_id === teacherId);
    const hasStudent = nextHistory.some((item) => item.recording_id === studentId);

    if (!hasTeacher && nextHistory[1]) {
      localStorage.setItem(PROSODY_TEACHER_KEY, nextHistory[1].recording_id);
    }
    if (!hasStudent && nextHistory[0]) {
      localStorage.setItem(PROSODY_STUDENT_KEY, nextHistory[0].recording_id);
    }
  }

  loadHistory() {
    return safeParseJson(localStorage.getItem(PROSODY_HISTORY_KEY) || '[]', []);
  }

  getTeacherId() {
    return localStorage.getItem(PROSODY_TEACHER_KEY) || '';
  }

  getStudentId() {
    return localStorage.getItem(PROSODY_STUDENT_KEY) || '';
  }

  setRole(role, recordingId) {
    if (role === 'teacher') {
      localStorage.setItem(PROSODY_TEACHER_KEY, recordingId);
    } else if (role === 'student') {
      localStorage.setItem(PROSODY_STUDENT_KEY, recordingId);
    }
    this.renderFromStorage();
  }

  renderFromStorage(currentId = '') {
    const history = this.loadHistory();
    const currentRecord = currentId ? history.find((item) => item.recording_id === currentId) : history[0];
    if (currentRecord) {
      this.renderCurrent(currentRecord);
    }
    this.renderHistory(history);
    this.renderComparison(history);
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
        ['Rate', formatMetricValue(summary.speech_rate)],
      ]
        .map(([label, value]) => `
          <div class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
            <div class="text-xs uppercase tracking-wide text-gray-500">${label}</div>
            <div class="text-sm font-semibold text-gray-800">${value === undefined || value === null ? '—' : value}</div>
          </div>`)
        .join('');
    }

    this.renderPlot(this.currentPlotEl, record, 'Current Recording');
    this.renderFeedback(record);
  }

  renderFeedback(record) {
    if (!this.feedbackEl) return;

    const summary = record.summary || {};
    this.feedbackEl.innerHTML = `
      <p><strong>Syllables:</strong> ${summary.syllable_count ?? '—'} estimated nuclei</p>
      <p><strong>Pauses:</strong> ${summary.pause_count ?? '—'} detected spans</p>
      <p><strong>Rhythm balance:</strong> ${formatMetricValue(summary.rhythm_balance)}</p>
      <p><strong>Mean speaking note:</strong> ${summary.mean_note ?? '—'} (${formatMetricValue(summary.mean_f0_hz, ' Hz')})</p>
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
        return `
          <div class="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="font-medium text-gray-800">Recording ${record.recording_id.slice(0, 6)}</div>
                <div class="text-xs text-gray-500">${createdAt}</div>
                <div class="mt-2 text-sm text-gray-700">
                  <span class="mr-3">Syllables: ${record.summary?.syllable_count ?? '—'}</span>
                  <span class="mr-3">Pauses: ${record.summary?.pause_count ?? '—'}</span>
                  <span>Balance: ${formatMetricValue(record.summary?.rhythm_balance)}</span>
                </div>
              </div>
              <div class="flex flex-col gap-2 text-xs">
                <button type="button" class="rounded bg-blue-600 px-3 py-1 font-medium text-white hover:bg-blue-700" data-role="teacher" data-recording-id="${record.recording_id}">
                  ${isTeacher ? 'Teacher sample' : 'Set as teacher'}
                </button>
                <button type="button" class="rounded bg-emerald-600 px-3 py-1 font-medium text-white hover:bg-emerald-700" data-role="student" data-recording-id="${record.recording_id}">
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

    this.renderPlot(this.teacherPlotEl, teacherRecord, 'Teacher Sample');
    this.renderPlot(this.studentPlotEl, studentRecord, 'Student Sample');
  }

  renderPlot(targetElement, record, title) {
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
    const config = { responsive: true, displayModeBar: true, scrollZoom: true };
    window.Plotly.newPlot(targetElement, chartData.traces, chartData.layout, config);
  }
}

function initializeProsodyLab() {
  const recordBtn = document.getElementById('prosody-record-btn');
  const recorderContainer = document.getElementById('prosody-recorder');
  if (!recordBtn || !recorderContainer) return;

  window.prosodyLabRecorder = new ProsodyLabRecorder();
  window.prosodyLabRecorder.init().catch((error) => {
    console.error('Failed to initialize Prosody Lab:', error);
  });

  const lockBtn = document.getElementById('prosody-lock-btn');
  const beatsSelect = document.getElementById('prosody-beats-select');
  const zoomSlider = document.getElementById('prosody-zoom-slider');
  const zoomLabel = document.getElementById('prosody-zoom-label');

  if (lockBtn) {
    lockBtn.addEventListener('click', () => {
      if (!window.prosodyLabRecorder) return;
      window.prosodyLabRecorder.locked = !window.prosodyLabRecorder.locked;
      lockBtn.classList.toggle('bg-blue-600', window.prosodyLabRecorder.locked);
      lockBtn.classList.toggle('text-white', window.prosodyLabRecorder.locked);
      lockBtn.classList.toggle('bg-white', !window.prosodyLabRecorder.locked);
      window.prosodyLabRecorder.renderFromStorage();
    });
  }

  if (beatsSelect) {
    beatsSelect.addEventListener('change', () => {
      if (!window.prosodyLabRecorder) return;
      const val = beatsSelect.value;
      if (val !== 'auto') {
        window.prosodyLabRecorder.beatsPerBar = parseInt(val, 10);
      }
      window.prosodyLabRecorder.renderFromStorage();
    });
  }

  if (zoomSlider && zoomLabel) {
    zoomSlider.addEventListener('input', () => {
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
