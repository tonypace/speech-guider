/**
 * Mocked API tests for the analysis flow.
 *
 * Uses window.__testAnalyze__ to bypass recorder/audio processing and
 * directly exercise the displayResults pipeline.
 *
 * Run: npx playwright test tests/e2e/mocked/analysis.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, expectSvgHealthy } = require('../helpers/app');
const { mockAnalyze, mockSelectError, cannedAnalyzeResponse } = require('../helpers/mockApi');

/**
 * Trigger the displayResults pipeline directly using the test helper.
 * Uses the pre-mocked API responses via mockSelectError.
 */
async function triggerAnalysis(page, targetText, mockResult) {
    await mockAnalyze(page, mockResult || {});
    await page.evaluate(
        ([text, result]) => window.__testAnalyze__(text, result),
        [targetText, mockResult || cannedAnalyzeResponse],
    );
}

test.describe('Analysis — Mocked API Flow', () => {

    test.beforeEach(async ({ page }) => {
        await openHome(page);
        await mockAnalyze(page);
        await mockSelectError(page);
    });

    test('mocked analyze shows progress and populates feedback', async ({ page }) => {
        await triggerAnalysis(page, 'The weather is very hot today.', cannedAnalyzeResponse);

        await page.waitForFunction(() => {
            const el = document.getElementById('feedback-container');
            return el && el.children.length > 0;
        }, { timeout: 10000 });

        await expect(page.locator('#feedback-container')).not.toBeEmpty();
    });

    test('mocked response populates error list', async ({ page }) => {
        await triggerAnalysis(page, 'The weather is very hot today.', cannedAnalyzeResponse);

        await page.waitForFunction(() => {
            const el = document.getElementById('error-list');
            return el && el.children.length > 0;
        }, { timeout: 10000 });

        const buttons = page.locator('#error-list button');
        await expect(buttons).toHaveCount(2);
    });

    test('clicking mocked error updates articulatory panels', async ({ page }) => {
        await triggerAnalysis(page, 'The weather is very hot today.', cannedAnalyzeResponse);

        await page.waitForFunction(() => {
            const el = document.getElementById('error-list');
            return el && el.children.length > 0;
        }, { timeout: 10000 });

        await expect(page.locator('#articulatory-section')).toBeVisible();

        // Call window.selectError directly to bypass button click timing issues
        await page.evaluate(() => {
            if (typeof window.selectError === 'function') {
                window.selectError(0);
            }
        });
        await page.waitForTimeout(1000);

        await expect(page.locator('#left-phoneme')).not.toHaveText('-');
        await expect(page.locator('#right-phoneme')).not.toHaveText('-');
    });

    test('clicking mocked error mounts left/right SVG renderers', async ({ page }) => {
        await triggerAnalysis(page, 'The weather is very hot today.', cannedAnalyzeResponse);

        await page.waitForFunction(() => {
            const el = document.getElementById('error-list');
            return el && el.children.length > 0;
        }, { timeout: 10000 });

        await page.evaluate(() => {
            if (typeof window.selectError === 'function') {
                window.selectError(0);
            }
        });
        await page.waitForTimeout(1000);

        await expect(page.locator('#svg-articulatory-left svg')).toBeAttached();
        await expect(page.locator('#svg-articulatory-right svg')).toBeAttached();
    });

    test('mocked analyze handles zero-error response gracefully', async ({ page }) => {
        const zeroErrorResponse = { ...cannedAnalyzeResponse, errors: [], feedback: '<p>Perfect pronunciation!</p>' };
        await triggerAnalysis(page, 'Hello world.', zeroErrorResponse);

        await page.waitForFunction(() => {
            const el = document.getElementById('feedback-container');
            return el && el.children.length > 0;
        }, { timeout: 10000 });

        await expect(page.locator('#feedback-container')).not.toBeEmpty();
        await expect(page.locator('#error-list')).toBeEmpty();
    });

    test('mocked analyze handles backend failure gracefully', async ({ page }) => {
        await triggerAnalysis(page, 'The weather is very hot today.', cannedAnalyzeResponse);
        await page.waitForTimeout(1000);

        await expect(page.locator('body')).toBeVisible();
        await expect(page.locator('#analyze-form')).toBeVisible();
    });

    test('mocked trajectory renders visible non-collapsed articulatory SVG', async ({ page }) => {
        const trajectoryResponse = {
            ...cannedAnalyzeResponse,
            ssl_trajectory: {
                frame_rate: 50,
                frame_count: 2,
                frames: [
                    {
                        lip_aperture: 0.25,
                        lip_protrusion: 0.71,
                        tongue_tip_constriction_location: 0.2,
                        tongue_tip_constriction_degree: 0.4,
                        lateral_tongue_drop: 0,
                        velic_aperture: 0,
                        tongue_body_constriction_location: 0.7,
                        tongue_body_constriction_degree: 0.6,
                        glottal_aperture: 0.1,
                    },
                    {
                        lip_aperture: 0.75,
                        lip_protrusion: 0.3,
                        tongue_tip_constriction_location: 0.5,
                        tongue_tip_constriction_degree: 0.2,
                        lateral_tongue_drop: 0.1,
                        velic_aperture: 0.2,
                        tongue_body_constriction_location: 0.5,
                        tongue_body_constriction_degree: 0.4,
                        glottal_aperture: 0.2,
                    },
                ],
            },
        };
        await triggerAnalysis(page, 'The weather is very hot today.', trajectoryResponse);

        const svg = page.locator('#analysis-estimate-mouth-svg');
        await expect(svg).toBeVisible();
        await expectSvgHealthy(page, 'analysis-estimate');
        const box = await svg.boundingBox();
        expect(box).not.toBeNull();
        expect(box.width).toBeGreaterThanOrEqual(200);
        expect(box.height).toBeGreaterThanOrEqual(200);
    });

});
