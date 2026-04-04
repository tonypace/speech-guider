/**
 * Real-backend smoke tests for the Animation Lab.
 *
 * These tests verify that the app loads, the SVG renderer mounts,
 * and geometry is non-empty — catching gross rendering regressions.
 * They do NOT assert phonetic correctness.
 *
 * Run: npx playwright test tests/e2e/real/animationLab.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, switchToTab, waitForSvgRenderer, expectSvgHealthy } = require('../helpers/app');

test.describe('Animation Lab — Real Backend Smoke', () => {

  test.beforeEach(async ({ page }) => {
    await openHome(page);
    await switchToTab(page, 'animation');
    await waitForSvgRenderer(page, '#svg-articulatory-animation');
  });

  test('loads animation lab and mounts svg renderer', async ({ page }) => {
    const svg = page.locator('#svg-articulatory-animation svg');
    await expect(svg).toBeAttached();

    // key structural nodes
    await expect(page.locator('#anim-tongue')).toBeAttached();
    await expect(page.locator('#anim-jaw-group')).toBeAttached();
    await expect(page.locator('#anim-glottis-hole')).toBeAttached();
    await expect(page.locator('#anim-oral-tract-fill')).toBeAttached();
    await expect(page.locator('#anim-nasal-tract-fill')).toBeAttached();
  });

  test('renders non-empty geometry on initial load', async ({ page }) => {
    // tongue d path must be drawn
    const tongueD = await page.locator('#anim-tongue').getAttribute('d');
    expect(tongueD).toBeTruthy();
    expect(tongueD.trim().length).toBeGreaterThan(5);

    // glottis-hole polygon must have points
    const glottisPts = await page.locator('#anim-glottis-hole').getAttribute('points');
    expect(glottisPts).toBeTruthy();
    expect(glottisPts.trim().length).toBeGreaterThan(3);

    // jaw-group must have a transform
    const jawTransform = await page.locator('#anim-jaw-group').getAttribute('transform');
    expect(jawTransform).toBeTruthy();
  });

  test('slider movement changes renderer geometry', async ({ page }) => {
    // capture initial tongue d
    const initialTongueD = await page.locator('#anim-tongue').getAttribute('d');
    const initialJawTransform = await page.locator('#anim-jaw-group').getAttribute('transform');

    // move LA slider — jaw should shift
    const laSlider = page.locator('#la-slider');
    await laSlider.fill('0.63');
    await page.waitForTimeout(100);

    const newJawTransform = await page.locator('#anim-jaw-group').getAttribute('transform');
    expect(newJawTransform).not.toBe(initialJawTransform);

    // move TTCL slider — tongue path should change
    const ttclSlider = page.locator('#ttcl-slider');
    await ttclSlider.fill('0.8');
    await page.waitForTimeout(100);

    const newTongueD = await page.locator('#anim-tongue').getAttribute('d');
    expect(newTongueD).not.toBe(initialTongueD);
  });

  test('selecting a phoneme updates selected badge and keeps svg healthy', async ({ page }) => {
    // click /p/ chip
    const pChip = page.locator('[data-phoneme="p"]');
    await pChip.click();

    const selectedBadge = page.locator('#selected-phoneme');
    await expect(selectedBadge).toHaveText('p');

    // save button should be enabled
    const saveBtn = page.locator('#save-position-btn');
    await expect(saveBtn).not.toBeDisabled();

    // renderer must still be healthy
    await expectSvgHealthy(page, 'anim');
  });

  test('save button works after phoneme selection', async ({ page }) => {
    const pChip = page.locator('[data-phoneme="p"]');
    await pChip.click();

    const saveBtn = page.locator('#save-position-btn');
    await saveBtn.click();

    const saveStatus = page.locator('#save-status');
    await expect(saveStatus).toBeVisible();
    const statusText = await saveStatus.textContent();
    expect(statusText.trim()).toBeTruthy();
  });

});
