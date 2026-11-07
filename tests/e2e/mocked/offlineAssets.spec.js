const { test, expect } = require('@playwright/test');
const { openHome, setRangeValue } = require('../helpers/app');

test('all tabs, preset styling and real plots work without external requests', async ({ page, context, baseURL }) => {
    const appOrigin = new URL(baseURL).origin;
    const externalRequests = [];
    await context.route('**/*', async (route) => {
        const { origin } = new URL(route.request().url());
        if (origin !== appOrigin) {
            externalRequests.push(route.request().url());
            await route.abort('internetdisconnected');
        } else {
            await route.continue();
        }
    });
    await page.addInitScript(() => {
        localStorage.setItem('prosodyLabHistory', JSON.stringify([{
            recording_id: 'offline-sample',
            summary: { syllable_count: 3, duration_seconds: 1.2, mean_f0_hz: 196, mean_note: 'G3' },
            pitch_track: [
                { time: 0, midi: 55, f0_hz: 196, note: 'G3', confidence: 0.9 },
                { time: 0.4, midi: 57, f0_hz: 220, note: 'A3', confidence: 0.9 },
                { time: 0.8, midi: 55, f0_hz: 196, note: 'G3', confidence: 0.9 },
                { time: 1.2, midi: 54, f0_hz: 185, note: 'F#3', confidence: 0.9 },
            ],
            syllable_onsets: [0, 0.4, 0.8],
        }]));
    });

    await openHome(page);
    await expect(page.locator('#tab-panel-analysis')).toBeVisible();
    await expect(page.locator('#tab-panel-animation')).toBeHidden();
    await page.evaluate(() => {
        window.__testAnalyze__('Offline exercise', { success: false, error: 'Try another recording.' });
    });
    await expect(page.getByText('Try another recording.')).toHaveCSS('color', 'rgb(185, 28, 28)');

    await page.locator('#tab-btn-animation').click();
    await expect(page.locator('#tab-panel-animation')).toBeVisible();
    await expect(page.locator('#tab-panel-analysis')).toBeHidden();
    await expect(page.locator('#svg-articulatory-animation svg')).toBeAttached();
    const phoneme = page.locator('[data-phoneme="i"]');
    await phoneme.click();
    await page.mouse.move(0, 0);
    await expect(phoneme).toHaveCSS('background-color', 'rgb(59, 130, 246)');
    await setRangeValue(page.locator('#tbcd-slider'), '0.42');
    await page.locator('#save-position-btn').click();
    await expect(page.locator('#save-status')).toHaveText('Saved!');
    await openHome(page);
    await page.locator('#tab-btn-animation').click();
    await phoneme.click();
    await expect(page.locator('#tbcd-val')).toHaveText('0.42');

    await page.locator('#tab-btn-prosody').click();
    await expect(page.locator('#tab-panel-prosody')).toBeVisible();
    await expect(page.locator('#prosody-current-plot .main-svg').first()).toBeVisible();
    expect(await page.evaluate(() => window.Plotly.version)).toBe('2.32.0');

    await page.locator('#tab-btn-comparison').click();
    await expect(page.locator('#tab-panel-comparison')).toBeVisible();
    await expect(page.locator('#tab-panel-prosody')).toBeHidden();
    expect(externalRequests).toEqual([]);
});
