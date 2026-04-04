/**
 * Mocked UI-flow tests for the Animation Lab.
 *
 * These tests use no real backend — API calls are unmocked so they hit
 * the network but we only assert frontend behavior.  They are fast and
 * deterministic.
 *
 * Run: npx playwright test tests/e2e/mocked/animationLab.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, switchToTab, waitForSvgRenderer } = require('../helpers/app');

test.describe('Animation Lab — Mocked UI Flow', () => {

  test.beforeEach(async ({ page }) => {
    await openHome(page);
    await switchToTab(page, 'animation');
    await waitForSvgRenderer(page, '#svg-articulatory-animation');
  });

  test('animation tab opens compact lab with all controls visible', async ({ page }) => {
    // left renderer column
    await expect(page.locator('#svg-articulatory-animation')).toBeVisible();
    // selected + save row
    await expect(page.locator('#selected-phoneme')).toBeVisible();
    await expect(page.locator('#save-position-btn')).toBeVisible();
    // phoneme strip
    await expect(page.locator('#phoneme-strip')).toBeVisible();
    // sliders
    await expect(page.locator('#la-slider')).toBeVisible();
    await expect(page.locator('#lp-slider')).toBeVisible();
    await expect(page.locator('#ttcl-slider')).toBeVisible();
    await expect(page.locator('#ttcd-slider')).toBeVisible();
    await expect(page.locator('#lat-slider')).toBeVisible();
    await expect(page.locator('#vel-slider')).toBeVisible();
    await expect(page.locator('#tbcl-slider')).toBeVisible();
    await expect(page.locator('#tbcd-slider')).toBeVisible();
    await expect(page.locator('#glo-slider')).toBeVisible();
  });

  test('clicking phoneme updates selected badge and enables save button', async ({ page }) => {
    const iChip = page.locator('[data-phoneme="i"]');
    await iChip.click();

    await expect(page.locator('#selected-phoneme')).toHaveText('i');

    const saveBtn = page.locator('#save-position-btn');
    await expect(saveBtn).not.toBeDisabled();
  });

  test('slider value labels update as controls move', async ({ page }) => {
    // move LA slider
    const laSlider = page.locator('#la-slider');
    await laSlider.fill('0.50');
    await laSlider.dispatchEvent('input');
    await expect(page.locator('#la-val')).toHaveText('0.50');

    // move TTCL slider — value shown with decimal
    const ttclSlider = page.locator('#ttcl-slider');
    await ttclSlider.fill('0.75');
    await ttclSlider.dispatchEvent('input');
    await expect(page.locator('#ttcl-val')).toHaveText('0.75');

    // move GLO slider
    const gloSlider = page.locator('#glo-slider');
    await gloSlider.fill('15');
    await gloSlider.dispatchEvent('input');
    await expect(page.locator('#glo-val')).toHaveText('15');
  });

  test('preset phoneme selection updates slider values', async ({ page }) => {
    // default state has LP=0.71; /u/ preset normalizes to a more protruded value
    const uChip = page.locator('[data-phoneme="u"]');
    await uChip.click();

    // LP should have changed from the default 0.71
    const lpVal = await page.locator('#lp-val').textContent();
    expect(parseFloat(lpVal)).toBeGreaterThan(0.71);

    // TBCL (tongue body) should also have changed from default 0.7
    const tbclVal = await page.locator('#tbcl-val').textContent();
    expect(parseFloat(tbclVal)).not.toBeCloseTo(0.7, 1);
  });

  test('save shows status feedback', async ({ page }) => {
    const pChip = page.locator('[data-phoneme="p"]');
    await pChip.click();

    const saveBtn = page.locator('#save-position-btn');
    await saveBtn.click();

    const saveStatus = page.locator('#save-status');
    await expect(saveStatus).toBeVisible();
    const text = await saveStatus.textContent();
    expect(text.trim()).toBeTruthy();
  });

  test('switching tabs and returning keeps renderer mounted', async ({ page }) => {
    // go to prosody
    await switchToTab(page, 'prosody');
    await page.waitForTimeout(300);

    // back to animation
    await switchToTab(page, 'animation');
    await page.waitForTimeout(300);

    // renderer must still be mounted and healthy
    await expect(page.locator('#svg-articulatory-animation svg')).toBeAttached();
    await expect(page.locator('#anim-tongue')).toBeAttached();
  });

  test('saving preset preserves state across page reload', async ({ page }) => {
    // select /k/
    const kChip = page.locator('[data-phoneme="k"]');
    await kChip.click();

    // tweak TBCD slider away from the template default (1.00 for /k/)
    const tbcdSlider = page.locator('#tbcd-slider');
    await tbcdSlider.fill('0.42');
    await tbcdSlider.dispatchEvent('input');

    // save
    await page.locator('#save-position-btn').click();
    await page.waitForTimeout(300);

    // reload
    await page.reload();
    await page.waitForLoadState('networkidle');
    await switchToTab(page, 'animation');
    await page.waitForTimeout(300);

    // re-select /k/
    await page.locator('[data-phoneme="k"]').click();
    await page.waitForTimeout(300);

    // TBCD should reflect saved custom state (not default 1.00 for /k/)
    const tbcdVal = await page.locator('#tbcd-val').textContent();
    expect(parseFloat(tbcdVal)).toBeCloseTo(0.42, 2);
  });

});
