/** Keep listener and microphone ownership local to a recorder instance. */
export function listen(owner, target, type, handler, options) {
    target.addEventListener(type, handler, options);
    owner.eventListeners.push([target, type, handler, options]);
}

export function releaseCapture(owner) {
    owner.stream?.getTracks().forEach((track) => track.stop());
    owner.stream = null;
    owner.visualizerSource?.disconnect();
    owner.visualizerSource = null;
    const context = owner.audioContext;
    owner.audioContext = null;
    if (context && context.state !== 'closed') {
        Promise.resolve(context.close()).catch((error) => console.warn('Audio close failed', error));
    }
}
