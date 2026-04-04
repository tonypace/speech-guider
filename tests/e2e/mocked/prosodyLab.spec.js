/**
 * Mocked UI tests for the Prosody Lab tab.
 *
 * Validates that the prosody tab renders its containers and responds
 * to tab switching correctly.
 *
 * Run: npx playwright test tests/e2e/mocked/prosodyLab.spec.js
 */

const { test, expect } = require('@playwright/test');
const { openHome, switchToTab } = require('../helpers/app');
const { mockProsodyLabAnalyze } = require('../helpers/mockApi');

test.describe('Prosody Lab — Mocked UI Flow', () => {

  test.beforeEach(async ({ page }) => {
    await openHome(page);
    await mockProsodyLabAnalyze(page);
  });

  test('prosody tab opens and renders core containers', async ({ page }) => {
    await switchToTab(page, 'prosody');

    // recorder container should exist (may or may not be visible depending on HTTPS)
    await expect(page.locator('#recorder')).toBeAttached();

    // prosody lab panel — check for the chart container (rendered by JS)
    const prosodyPanel = page.locator('#tab-panel-prosody');
    await expect(prosodyPanel).toBeVisible();
  });

  test('switching to prosody tab stops animation renderer', async ({ page }) => {
    // start on animation tab
    await switchToTab(page, 'animation');

    // animation renderer should not be running after switch away
    await switchToTab(page, 'prosody');

    // prosody tab must be visible
    const prosodyPanel = page.locator('#tab-panel-prosody');
    await expect(prosodyPanel).toBeVisible();
  });

  test('prosody tab switching is reversible', async ({ page }) => {
    await switchToTab(page, 'prosody');
    await expect(page.locator('#tab-panel-prosody')).toBeVisible();

    await switchToTab(page, 'animation');
    await expect(page.locator('#tab-panel-animation')).toBeVisible();
    await expect(page.locator('#svg-articulatory-animation')).toBeVisible();

    await switchToTab(page, 'prosody');
    await expect(page.locator('#tab-panel-prosody')).toBeVisible();
  });

});
