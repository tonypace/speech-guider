import { releaseCapture } from './capture_resources.js';
import { getSettings, listMicrophones, microphoneError, openMicrophone } from './microphone.js';

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
    const capture = {};
    let inputs = [];
    let generation = 0;
    let timer;
    let animation;
    let url;
    let recorder;

    const updateMicrophoneControls = () => {
        devices.disabled = !enabled.checked;
        refresh.disabled = !enabled.checked;
        test.disabled = !enabled.checked;
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

    window.addEventListener('beforeunload', closeTest);
    window.addEventListener('speechguider:tabchange', event => {
        if (event.detail !== 'settings') closeTest();
    });
    enabled.addEventListener('change', () => {
        if (!enabled.checked) closeTest();
        updateMicrophoneControls();
    });
    devices.addEventListener('change', closeTest);
    refresh.addEventListener('click', async () => {
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
            updateMicrophoneControls();
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
    updateMicrophoneControls();
    renderDevices(settings.microphone_device_id, settings.microphone_label).catch(error => {
        status.textContent = microphoneError(error);
    });
}

document.addEventListener('DOMContentLoaded', initializeSettings);
