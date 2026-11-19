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

        // prosody lab panel — check for the chart container and Goal 1 / Goal 2 SVG stages
        const prosodyPanel = page.locator('#tab-panel-prosody');
        await expect(prosodyPanel).toBeVisible();
        await expect(page.locator('#prosody-tether-stage svg')).toBeVisible();
        await expect(page.locator('#prosody-flow-stage svg')).toBeHidden();
        await page.locator('#prosody-view-tab-live').click();
        await expect(page.locator('#prosody-flow-stage svg')).toBeVisible();
        await expect(page.locator('#prosody-tether-stage svg')).toBeHidden();
    });

    test('switching from analysis to prosody hides analysis panel', async ({ page }) => {
        await switchToTab(page, 'analysis');
        await expect(page.locator('#tab-panel-analysis')).toBeVisible();

        await switchToTab(page, 'prosody');
        await expect(page.locator('#tab-panel-prosody')).toBeVisible();
        await expect(page.locator('#tab-panel-analysis')).toBeHidden();
    });

    test('tab switching across analysis, prosody, comparison, and settings is reversible', async ({ page }) => {
        await switchToTab(page, 'prosody');
        await expect(page.locator('#tab-panel-prosody')).toBeVisible();

        await switchToTab(page, 'comparison');
        await expect(page.locator('#tab-panel-comparison')).toBeVisible();
        await expect(page.locator('#tab-panel-prosody')).toBeHidden();

        await switchToTab(page, 'settings');
        await expect(page.locator('#tab-panel-settings')).toBeVisible();
        await expect(page.locator('#tab-panel-comparison')).toBeHidden();

        await switchToTab(page, 'analysis');
        await expect(page.locator('#tab-panel-analysis')).toBeVisible();
        await expect(page.locator('#tab-panel-settings')).toBeHidden();

        await switchToTab(page, 'prosody');
        await expect(page.locator('#tab-panel-prosody')).toBeVisible();
        await expect(page.locator('#tab-panel-analysis')).toBeHidden();
    });

});
