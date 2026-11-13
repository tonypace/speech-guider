/** Share microphone preferences across the app's recording entry points. */
export function getSettings() {
    return window.__SPEECH_GUIDER_SETTINGS__ || {};
}

export async function listMicrophones() {
    const devices = await navigator.mediaDevices?.enumerateDevices?.() || [];
    return devices.filter(device => device.kind === 'audioinput');
}

export function microphoneError(error) {
    if (error.name === 'NotAllowedError') return 'Microphone permission was denied. Check browser or macOS permissions.';
    if (error.name === 'NotFoundError' || error.name === 'OverconstrainedError') {
        return 'Microphone unavailable. Reconnect it or choose System default in Settings.';
    }
    return error.message || 'Could not open the microphone.';
}

export async function openMicrophone(settings = getSettings()) {
    if (settings.microphone_enabled === false) throw new Error('Microphone is off in Settings.');
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone access is unavailable.');
    // Preserve speech dynamics for analysis by opting out of browser voice processing.
    const audio = { autoGainControl: false, noiseSuppression: false, echoCancellation: false };
    const id = settings.microphone_device_id;
    if (id) {
        // WebView origins change across desktop launches. Use a unique label if its ID changed.
        const devices = await listMicrophones();
        const labels = settings.microphone_label ? devices.filter(device => device.label === settings.microphone_label) : [];
        const match = devices.find(device => device.deviceId === id) || (labels.length === 1 ? labels[0] : null);
        audio.deviceId = { exact: match?.deviceId || id };
    }
    return navigator.mediaDevices.getUserMedia({ audio });
}
