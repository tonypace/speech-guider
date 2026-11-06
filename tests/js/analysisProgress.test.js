import { afterEach, describe, expect, it, vi } from 'vitest';
import { openAnalysisProgress } from '../../static/js/analysis_progress.js';

afterEach(() => vi.unstubAllGlobals());

describe('analysis progress reservation', () => {
    it('reserves before streaming and closes on terminal events', async () => {
        const handlers = {};
        const close = vi.fn();
        const Source = vi.fn(function(url) {
            this.url = url;
            this.close = close;
            this.addEventListener = (event, handler) => { handlers[event] = handler; };
        });
        vi.stubGlobal('EventSource', Source);
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: true, json: async () => ({ job_id: 'reserved' })
        }));
        const update = vi.fn();
        const progress = await openAnalysisProgress(update);
        expect(fetch).toHaveBeenCalledWith('/api/analysis-jobs', { method: 'POST' });
        expect(Source).toHaveBeenCalledWith('/api/progress/reserved');
        expect(progress.jobId).toBe('reserved');
        handlers.progress({ data: '{"message":"Running","progress":0.6}' });
        expect(update).toHaveBeenCalledWith({ message: 'Running', progress: 0.6 });
        handlers.failed({ data: '{"status":"failed"}' });
        expect(close).toHaveBeenCalledOnce();
    });

    it('preserves synchronous analysis when reservation fails', async () => {
        vi.stubGlobal('EventSource', vi.fn());
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
        expect(await openAnalysisProgress(vi.fn())).toBeNull();
        expect(EventSource).not.toHaveBeenCalled();
    });
});
