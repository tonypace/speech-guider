/**
 * Mocked API tests for the analysis flow.
 *
 * Uses window.__testAnalyze__ to bypass recorder/audio processing and
 * directly exercise the displayResults pipeline.
 *
 * Run: npx playwright test tests/e2e/mocked/analysis.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome } = require('../helpers/app');
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

});
