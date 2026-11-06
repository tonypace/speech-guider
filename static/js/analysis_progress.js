/** Reserve progress before upload; HTTP analysis remains usable without SSE. */
export async function openAnalysisProgress(onProgress) {
    if (typeof EventSource !== 'function') return null;
    try {
        const response = await fetch('/api/analysis-jobs', { method: 'POST' });
        if (!response.ok) return null;
        const reservation = await response.json();
        if (!reservation.job_id) return null;
        const source = new EventSource(`/api/progress/${encodeURIComponent(reservation.job_id)}`);
        const update = (event) => {
            try {
                onProgress(JSON.parse(event.data));
            } catch (error) {
                console.warn('Invalid progress event', error);
            }
        };
        source.addEventListener('progress', update);
        for (const terminal of ['complete', 'failed', 'cancelled']) {
            source.addEventListener(terminal, (event) => {
                update(event);
                source.close();
            });
        }
        source.addEventListener('expired', () => source.close());
        return { jobId: reservation.job_id, close: () => source.close() };
    } catch (error) {
        console.warn('Progress unavailable', error);
        return null;
    }
}
