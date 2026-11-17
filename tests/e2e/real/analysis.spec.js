/**
 * Real-backend smoke tests for the analysis flow.
 *
 * These tests verify the app handles a real audio upload and analysis
 * end-to-end. They pass whether or not pronunciation errors are detected —
 * their job is to catch wiring and rendering regressions, not to validate
 * phonetic correctness.
 *
 * Run: npx playwright test tests/e2e/real/analysis.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, waitForAnalysisDone, expectSvgHealthy } = require('../helpers/app');

const FIXTURE_PATH = 'tests/e2e/fixtures/test-audio.wav';

async function disableMicrophone(page) {
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'mediaDevices', {
            configurable: true,
            value: undefined,
        });
    });
}

async function uploadFixtureAudio(page, targetText) {
    await page.fill('#target_text', targetText);
    const responsePromise = page.waitForResponse(
        (response) => response.url().includes('/api/analyze') && response.request().method() === 'POST',
        { timeout: 60000 },
    );
    await page.locator('#audio').setInputFiles(FIXTURE_PATH);
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    await waitForAnalysisDone(page, 60000);
    return response;
}

test.describe('Analysis — Real Backend Smoke', () => {
    test.describe.configure({ mode: 'serial' });

    test('reveals file upload fallback when microphone API is unavailable', async ({ page }) => {
        await disableMicrophone(page);
        await openHome(page);

        await expect(page.locator('#browser-error-msg')).toBeVisible();
        await expect(page.locator('#file-upload-section')).toBeVisible();
        await expect(page.locator('#audio')).toBeVisible();
    });

    test('submits real analysis via #audio upload and renders feedback without crashing', async ({ page }) => {
        await disableMicrophone(page);
        await openHome(page);
        await uploadFixtureAudio(page, 'The weather is very hot today.');

        await expect(page.locator('#feedback-container')).not.toBeEmpty();
        await expect(page.locator('#progress-container')).toBeHidden();
        await expect(page.locator('#analyze-form')).toBeVisible();
    });

    test('analysis passes even when no pronunciation errors are detected', async ({ page }) => {
        await disableMicrophone(page);
        await openHome(page);
        await uploadFixtureAudio(page, 'Hello world.');

        await expect(page.locator('#feedback-container')).not.toBeEmpty();
        await expect(page.locator('#analyze-form')).toBeVisible();
    });

    test('if errors exist, clicking one mounts healthy left/right renderers and updates labels', async ({ page }) => {
        await disableMicrophone(page);
        await openHome(page);
        await uploadFixtureAudio(page, 'The weather is very hot today.');

        const errorButtons = page.locator('#error-list button');
        if (await errorButtons.count() === 0) return;

        const leftLabelBefore = await page.locator('#left-phoneme').textContent();
        const rightLabelBefore = await page.locator('#right-phoneme').textContent();

        await errorButtons.first().click();
        await expect(page.locator('#svg-articulatory-left svg')).toBeAttached();
        await expect(page.locator('#svg-articulatory-right svg')).toBeAttached();
        await expectSvgHealthy(page, 'left');
        await expectSvgHealthy(page, 'right');

        const leftLabel = await page.locator('#left-phoneme').textContent();
        const rightLabel = await page.locator('#right-phoneme').textContent();
        expect(leftLabel.trim()).not.toBe('-');
        expect(rightLabel.trim()).not.toBe('-');
        expect(leftLabel !== leftLabelBefore || rightLabel !== rightLabelBefore).toBe(true);
    });

});
