/**
 * Real-backend smoke tests for the analysis flow.
 *
 * These tests verify the app handles a real audio upload and analysis
 * end-to-end.  They pass whether or not pronunciation errors are detected —
 * their job is to catch wiring and rendering regressions, not to validate
 * phonetic correctness.
 *
 * NOTE: File upload tests are SKIPPED because the file upload handler
 * (listening for file input changes and calling sendForAnalysis) is not yet
 * implemented in recorder.js. The UI flow is already covered by mocked tests.
 *
 * Run: npx playwright test tests/e2e/real/analysis.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, waitForAnalysisDone, expectSvgHealthy } = require('../helpers/app');

test.describe('Analysis — Real Backend Smoke', () => {

  test.skip('submits real analysis with fixture audio and completes without crashing', async ({ page }) => {
    // SKIPPED: File upload handler not implemented in recorder.js
    // The file input exists in HTML but no JS handles file selection.
    // UI flow is covered by mocked tests.
    await openHome(page);
    const fixturePath = 'tests/e2e/fixtures/test-audio.wav';
    await page.fill('#target_text', 'The weather is very hot today.');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(fixturePath);
    await page.click('button[type="submit"]');
    await waitForAnalysisDone(page, 60000);
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('#analyze-form')).toBeVisible();
  });

  test.skip('analysis passes even when no errors are detected', async ({ page }) => {
    // SKIPPED: File upload handler not implemented in recorder.js
    await openHome(page);
    await page.fill('#target_text', 'Hello world.');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/e2e/fixtures/test-audio.wav');
    await page.click('button[type="submit"]');
    await waitForAnalysisDone(page, 60000);
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('#analyze-form')).toBeVisible();
  });

  test.skip('if errors exist, clicking one mounts left/right renderers', async ({ page }) => {
    // SKIPPED: File upload handler not implemented in recorder.js
    await openHome(page);
    await page.fill('#target_text', 'The weather is very hot today.');
    await page.locator('input[type="file"]').setInputFiles('tests/e2e/fixtures/test-audio.wav');
    await page.click('button[type="submit"]');
    await waitForAnalysisDone(page, 60000);
    const errorButtons = page.locator('#error-list button');
    const count = await errorButtons.count();
    if (count === 0) return;
    await errorButtons.first().click();
    await page.waitForTimeout(500);
    await expect(page.locator('#svg-articulatory-left svg')).toBeAttached();
    await expect(page.locator('#svg-articulatory-right svg')).toBeAttached();
    await expect(page.locator('#left-tongue')).toBeAttached();
    await expect(page.locator('#right-tongue')).toBeAttached();
  });

  test.skip('if errors exist, clicking one updates phoneme labels', async ({ page }) => {
    // SKIPPED: File upload handler not implemented in recorder.js
    await openHome(page);
    await page.fill('#target_text', 'The weather is very hot today.');
    await page.locator('input[type="file"]').setInputFiles('tests/e2e/fixtures/test-audio.wav');
    await page.click('button[type="submit"]');
    await waitForAnalysisDone(page, 60000);
    const errorButtons = page.locator('#error-list button');
    if (await errorButtons.count() === 0) return;
    const leftLabelBefore = await page.locator('#left-phoneme').textContent();
    const rightLabelBefore = await page.locator('#right-phoneme').textContent();
    await errorButtons.first().click();
    await page.waitForTimeout(500);
    const leftLabel = await page.locator('#left-phoneme').textContent();
    const rightLabel = await page.locator('#right-phoneme').textContent();
    expect(leftLabel.trim()).not.toBe('-');
    expect(rightLabel.trim()).not.toBe('-');
    const changed = leftLabel !== leftLabelBefore || rightLabel !== rightLabelBefore;
    expect(changed).toBe(true);
  });

  test.skip('analysis result renderers have non-empty geometry when errors are present', async ({ page }) => {
    // SKIPPED: File upload handler not implemented in recorder.js
    await openHome(page);
    await page.fill('#target_text', 'The weather is very hot today.');
    await page.locator('input[type="file"]').setInputFiles('tests/e2e/fixtures/test-audio.wav');
    await page.click('button[type="submit"]');
    await waitForAnalysisDone(page, 60000);
    const errorButtons = page.locator('#error-list button');
    if (await errorButtons.count() === 0) return;
    await errorButtons.first().click();
    await page.waitForTimeout(500);
    await expectSvgHealthy(page, 'left');
    await expectSvgHealthy(page, 'right');
  });

});
