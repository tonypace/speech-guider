import { releaseCapture } from './capture_resources.js';
import { getSettings, listMicrophones, microphoneError, openMicrophone } from './microphone.js';
import {
    DEFAULT_REMOTE_BINDINGS,
    REMOTE_ACTIONS,
    formatRemoteKeyLabel,
    normalizeRemoteKey,
} from './remote_controller.js';

function initializeSettings() {
    const form = document.getElementById('settings-form');
    if (!form) return;
    const contact = document.getElementById('settings-contact');
    const enabled = document.getElementById('settings-mic-enabled');
    const devices = document.getElementById('settings-mic-device');
    const refresh = document.getElementById('settings-refresh-devices');
    const test = document.getElementById('settings-mic-test');
    const player = document.getElementById('settings-test-playback');
    const level = document.getElementById('settings-mic-level');
    const status = document.getElementById('settings-mic-status');
    const saveStatus = document.getElementById('settings-save-status');
    const save = document.getElementById('settings-save');
    const remoteEnabled = document.getElementById('settings-remote-enabled');
    const remoteRecordMode = document.getElementById('settings-remote-record-mode');
    const remoteStatus = document.getElementById('settings-remote-status');
    const remoteMacosBox = document.getElementById('settings-remote-macos-box');
    const remotePermissionStatus = document.getElementById('settings-remote-permission-status');
    const remotePermissionBtn = document.getElementById('settings-remote-permission-btn');
    const remotePermissionRefresh = document.getElementById('settings-remote-permission-refresh');
    const assignButtons = Array.from(form.querySelectorAll('[data-remote-assign]'));
    const clearButtons = Array.from(form.querySelectorAll('[data-remote-clear]'));
    const capture = {};
    let inputs = [];
    let generation = 0;
    let timer;
    let animation;
    let url;
    let recorder;
    let learningAction = null;
    let fallbackLearnListener = null;
    const remoteBindings = { ...DEFAULT_REMOTE_BINDINGS };

    const updateMicrophoneControls = () => {
        devices.disabled = !enabled.checked;
        refresh.disabled = !enabled.checked;
        test.disabled = !enabled.checked;
    };

    const renderRemoteBindings = () => {
        const isRemoteOn = remoteEnabled ? remoteEnabled.checked : true;
        if (remoteRecordMode) remoteRecordMode.disabled = !isRemoteOn;
        for (const action of REMOTE_ACTIONS) {
            const badge = form.querySelector(`[data-remote-binding="${action}"]`);
            if (badge) badge.textContent = formatRemoteKeyLabel(remoteBindings[action]);
        }
        assignButtons.forEach((btn) => {
            const action = btn.getAttribute('data-remote-assign');
            const isListening = learningAction === action;
            btn.disabled = !isRemoteOn;
            btn.textContent = isListening ? 'Press remote button…' : 'Assign button';
            btn.classList.toggle('bg-blue-600', isListening);
            btn.classList.toggle('text-white', isListening);
            btn.classList.toggle('text-blue-600', !isListening);
        });
        clearButtons.forEach((btn) => {
            const action = btn.getAttribute('data-remote-clear');
            btn.disabled = !isRemoteOn || !remoteBindings[action];
        });
    };

    const stopLearning = (message = '') => {
        learningAction = null;
        if (fallbackLearnListener) {
            document.removeEventListener('keydown', fallbackLearnListener, true);
            fallbackLearnListener = null;
        }
        window.remoteController?.setLearningCallback?.(null);
        if (remoteStatus && message) remoteStatus.textContent = message;
        renderRemoteBindings();
    };

    const applyRemoteSettingsLive = () => {
        const previous = getSettings();
        const next = {
            ...previous,
            remote_enabled: remoteEnabled ? remoteEnabled.checked : (previous.remote_enabled !== false),
            remote_record_mode: remoteRecordMode
                ? (remoteRecordMode.value === 'hold' ? 'hold' : 'toggle')
                : (previous.remote_record_mode === 'hold' ? 'hold' : 'toggle'),
            remote_bindings: { ...remoteBindings },
        };
        window.__SPEECH_GUIDER_SETTINGS__ = next;
        window.dispatchEvent(new CustomEvent('speechguider:settingschange', { detail: { previous, next } }));
        return next;
    };

    let remotePersistSeq = 0;
    const persistRemoteSettings = async (savedMessage = '', fallbackMessage = '') => {
        const next = applyRemoteSettingsLive();
        const seq = ++remotePersistSeq;
        if (typeof fetch !== 'function') {
            if (remoteStatus && fallbackMessage) remoteStatus.textContent = fallbackMessage;
            return;
        }
        try {
            const payload = {
                contact_enabled: next.contact_enabled !== false,
                microphone_enabled: next.microphone_enabled !== false,
                microphone_device_id: next.microphone_device_id || '',
                microphone_label: next.microphone_label || '',
                remote_enabled: next.remote_enabled !== false,
                remote_record_mode: next.remote_record_mode === 'hold' ? 'hold' : 'toggle',
                remote_bindings: { ...remoteBindings },
            };
            const response = await fetch('/api/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) throw new Error('Could not save settings.');
            const persisted = await response.json();
            if (seq === remotePersistSeq) {
                window.__SPEECH_GUIDER_SETTINGS__ = persisted;
                if (remoteStatus && savedMessage) remoteStatus.textContent = savedMessage;
            }
        } catch {
            if (seq === remotePersistSeq && remoteStatus && fallbackMessage) {
                remoteStatus.textContent = fallbackMessage;
            }
        }
    };

    const applyLearnedKey = (action, result) => {
        if (!result || result.cancelled) {
            stopLearning('Button assignment cancelled.');
            return;
        }
        const key = normalizeRemoteKey(result.key);
        if (!key) {
            stopLearning('Button not recognized. Try another remote button.');
            return;
        }
        let replacedAction = null;
        for (const other of REMOTE_ACTIONS) {
            if (other !== action && remoteBindings[other] === key) {
                remoteBindings[other] = '';
                replacedAction = other;
            }
        }
        remoteBindings[action] = key;
        const label = formatRemoteKeyLabel(key);
        const fallbackNote = replacedAction
            ? `Assigned ${label} (cleared previous binding). Click Save settings to keep.`
            : `Assigned ${label}. Click Save settings to keep.`;
        const savedNote = replacedAction
            ? `Assigned ${label} (cleared previous binding) and saved.`
            : `Assigned ${label} and saved.`;
        stopLearning(fallbackNote);
        void persistRemoteSettings(savedNote, fallbackNote);
    };

    const startLearning = (action) => {
        if (learningAction === action) {
            stopLearning('Button assignment cancelled.');
            return;
        }
        stopLearning();
        learningAction = action;
        renderRemoteBindings();
        if (remoteStatus) {
            remoteStatus.textContent = 'Press a button on your presenter remote (Esc to cancel)…';
        }
        if (window.remoteController?.setLearningCallback) {
            window.remoteController.setLearningCallback((result) => applyLearnedKey(action, result));
        } else {
            fallbackLearnListener = (event) => {
                const key = normalizeRemoteKey(event);
                if (!key || event.repeat) return;
                event.preventDefault();
                event.stopImmediatePropagation();
                applyLearnedKey(action, key === 'Escape' ? { cancelled: true } : { key });
            };
            document.addEventListener('keydown', fallbackLearnListener, true);
        }
    };

    const refreshMacosPermission = async (requestPrompt = false) => {
        if (!remoteMacosBox || !window.remoteController) return;
        const result = requestPrompt
            ? await window.remoteController.requestMediaKeyPermission()
            : await window.remoteController.getMediaKeyStatus();
        if (!result?.supported) {
            remoteMacosBox.classList.add('hidden');
            return;
        }
        remoteMacosBox.classList.remove('hidden');
        if (result.permission_granted) {
            if (remotePermissionStatus) {
                remotePermissionStatus.textContent = 'macOS volume & media button capture is ready (only active while Speech Guider is focused).';
            }
            if (remotePermissionBtn) remotePermissionBtn.hidden = true;
        } else {
            if (remotePermissionStatus) {
                remotePermissionStatus.textContent = 'To map Volume Up / Down buttons on macOS, grant Accessibility permission to Speech Guider, then click Re-check permission.';
            }
            if (remotePermissionBtn) remotePermissionBtn.hidden = false;
        }
    };

    const renderDevices = async (id, label) => {
        inputs = await listMicrophones();
        const selected = inputs.find(device => device.deviceId && device.deviceId === id);
        const matchingLabels = label ? inputs.filter(device => device.deviceId && device.label === label) : [];
        const matchedId = selected?.deviceId || (matchingLabels.length === 1 ? matchingLabels[0].deviceId : id);
        devices.replaceChildren(new Option('System default', ''));
        inputs.filter(device => device.deviceId).forEach((device, index) => {
            devices.add(new Option(device.label || `Microphone ${index + 1}`, device.deviceId));
        });
        if (matchedId && !Array.from(devices.options).some(option => option.value === matchedId)) {
            devices.add(new Option(`${label || 'Saved microphone'} (unavailable)`, matchedId));
        }
        devices.value = matchedId || '';
    };

    const draft = () => ({
        contact_enabled: contact.checked,
        microphone_enabled: enabled.checked,
        microphone_device_id: devices.value,
        microphone_label: inputs.find(device => device.deviceId === devices.value)?.label || (
            devices.value && devices.value === getSettings().microphone_device_id ? getSettings().microphone_label : ''
        ) || '',
        remote_enabled: remoteEnabled ? remoteEnabled.checked : (getSettings().remote_enabled !== false),
        remote_record_mode: remoteRecordMode
            ? (remoteRecordMode.value === 'hold' ? 'hold' : 'toggle')
            : (getSettings().remote_record_mode === 'hold' ? 'hold' : 'toggle'),
        remote_bindings: { ...remoteBindings },
    });

    const stopTest = () => {
        generation++;
        clearTimeout(timer);
        cancelAnimationFrame(animation);
        if (recorder?.state === 'recording') recorder.stop();
        recorder = null;
        releaseCapture(capture);
        level.value = 0;
        test.textContent = 'Test microphone';
    };

    const clearPlayback = () => {
        if (url) {
            player.pause();
            player.removeAttribute('src');
            URL.revokeObjectURL(url);
            url = null;
        }
        player.hidden = true;
    };

    const closeTest = () => {
        stopTest();
        clearPlayback();
        status.textContent = '';
    };

    window.addEventListener('beforeunload', () => {
        closeTest();
        stopLearning();
    });
    window.addEventListener('speechguider:tabchange', event => {
        if (event.detail !== 'settings') {
            closeTest();
            stopLearning();
        } else {
            void refreshMacosPermission(false);
        }
    });
    remoteEnabled?.addEventListener('change', () => {
        if (!remoteEnabled.checked) stopLearning();
        renderRemoteBindings();
        void persistRemoteSettings();
    });
    remoteRecordMode?.addEventListener('change', () => {
        void persistRemoteSettings();
    });
    assignButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-remote-assign');
            if (action) startLearning(action);
        });
    });
    clearButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-remote-clear');
            if (!action) return;
            if (learningAction === action) stopLearning();
            remoteBindings[action] = '';
            renderRemoteBindings();
            if (remoteStatus) remoteStatus.textContent = 'Binding cleared. Click Save settings to keep.';
            void persistRemoteSettings('Binding cleared and saved.', 'Binding cleared. Click Save settings to keep.');
        });
    });
    remotePermissionBtn?.addEventListener('click', () => {
        void refreshMacosPermission(true);
    });
    remotePermissionRefresh?.addEventListener('click', () => {
        void refreshMacosPermission(false);
    });
    enabled.addEventListener('change', () => {
        if (!enabled.checked) closeTest();
        updateMicrophoneControls();
    });
    devices.addEventListener('change', closeTest);
    let refreshInFlight = false;
    async function refreshMicrophones() {
        if (!enabled.checked || refreshInFlight) return;
        refreshInFlight = true;
        closeTest();
        const request = generation;
        refresh.disabled = true;
        status.textContent = 'Checking microphone permissions…';
        let stream;
        try {
            stream = await openMicrophone({ microphone_enabled: enabled.checked });
            if (request !== generation) return;
            const selection = draft();
            await renderDevices(selection.microphone_device_id, selection.microphone_label);
            if (request === generation) status.textContent = 'Microphone list refreshed.';
        } catch (error) {
            if (request === generation) status.textContent = microphoneError(error);
        } finally {
            stream?.getTracks().forEach(track => track.stop());
            refreshInFlight = false;
            updateMicrophoneControls();
        }
    }

    refresh.addEventListener('click', refreshMicrophones);
    window.addEventListener('speechguider:tabchange', (event) => {
        if (event.detail === 'settings' && enabled.checked) {
            void refreshMicrophones();
        }
    });

    test.addEventListener('click', async () => {
        if (test.textContent === 'Cancel test') {
            closeTest();
            return;
        }
        closeTest();
        const request = generation;
        test.textContent = 'Cancel test';
        status.textContent = 'Opening microphone…';
        try {
            const context = new (window.AudioContext || window.webkitAudioContext)();
            capture.audioContext = context;
            void context.resume().catch(() => {});
            const stream = await openMicrophone(draft());
            if (request !== generation) {
                stream.getTracks().forEach(track => track.stop());
                return;
            }
            capture.stream = stream;
            const source = context.createMediaStreamSource(stream);
            capture.visualizerSource = source;
            const analyser = context.createAnalyser();
            source.connect(analyser);
            const samples = new Float32Array(analyser.fftSize);
            const meter = () => {
                analyser.getFloatTimeDomainData(samples);
                const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
                level.value = Math.min(1, rms * 4);
                animation = requestAnimationFrame(meter);
            };
            recorder = new MediaRecorder(stream);
            const chunks = [];
            recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
            const name = stream.getAudioTracks()[0]?.label || 'Selected microphone';
            const mimeType = recorder.mimeType;
            recorder.onstop = () => {
                if (request !== generation) return;
                stopTest();
                if (!chunks.length) {
                    status.textContent = 'No test audio was captured.';
                    return;
                }
                url = URL.createObjectURL(new Blob(chunks, { type: mimeType || chunks[0].type }));
                player.src = url;
                player.hidden = false;
                status.textContent = `Test ready from ${name}. Play it back below.`;
            };
            recorder.onerror = () => {
                if (request !== generation) return;
                stopTest();
                status.textContent = 'Microphone test failed. Check the input and try again.';
            };
            recorder.start();
            meter();
            status.textContent = `Recording from ${name}. Speak for three seconds.`;
            timer = setTimeout(() => recorder?.stop(), 3000);
        } catch (error) {
            if (request !== generation) return;
            stopTest();
            status.textContent = microphoneError(error);
        }
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (save.disabled) return;
        closeTest();
        save.disabled = true;
        saveStatus.textContent = 'Saving…';
        try {
            const previous = getSettings();
            const response = await fetch('/api/settings', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draft()),
            });
            if (!response.ok) throw new Error('Could not save settings.');
            const next = await response.json();
            window.__SPEECH_GUIDER_SETTINGS__ = next;
            window.dispatchEvent(new CustomEvent('speechguider:settingschange', { detail: { previous, next } }));
            saveStatus.textContent = 'Settings saved.';
        } catch (error) {
            saveStatus.textContent = error.message;
        } finally {
            save.disabled = false;
        }
    });

    const settings = getSettings();
    contact.checked = settings.contact_enabled !== false;
    enabled.checked = settings.microphone_enabled !== false;
    if (remoteEnabled) remoteEnabled.checked = settings.remote_enabled !== false;
    if (remoteRecordMode) remoteRecordMode.value = settings.remote_record_mode === 'hold' ? 'hold' : 'toggle';
    for (const action of REMOTE_ACTIONS) {
        remoteBindings[action] = normalizeRemoteKey(settings.remote_bindings?.[action] || '');
    }
    updateMicrophoneControls();
    renderRemoteBindings();
    void refreshMacosPermission(false);
    renderDevices(settings.microphone_device_id, settings.microphone_label).catch(error => {
        status.textContent = microphoneError(error);
    });
}

document.addEventListener('DOMContentLoaded', initializeSettings);
