/**
 * Shared helpers for E2E tests.
 * Provides reusable primitives for opening pages, switching tabs,
 * asserting SVG renderer health, and waiting for analysis.
 */

/**
 * Navigate to the app home page and wait for it to be ready.
 * @param {import('@playwright/test').Page} page
 */
async function openHome(page) {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

/**
 * Switch to a tab by name.
 * @param {import('@playwright/test').Page} page
 * @param {'analysis' | 'animation' | 'prosody'} tabName
 */
async function switchToTab(page, tabName) {
  const btn = page.locator(`#tab-btn-${tabName}`);
  await btn.click();
  await page.waitForTimeout(200);
}

/**
 * Assert the SVG renderer has mounted inside a given container.
 * Fails fast if the container is empty or the SVG root is missing.
 * @param {import('@playwright/test').Page} page
 * @param {string} containerSelector  e.g. '#svg-articulatory-animation'
 */
async function waitForSvgRenderer(page, containerSelector) {
  const container = page.locator(containerSelector);
  await container.waitFor({ state: 'attached' });
  const svg = container.locator('svg');
  await svg.waitFor({ state: 'attached' });
}

/**
 * Assert that a mounted SVG renderer has non-trivial geometry on key nodes.
 * This catches completely blank/broken rendering.
 * @param {import('@playwright/test').Page} page
 * @param {string} prefix  SVG element prefix used at mount time, e.g. 'anim', 'left', 'right'
 */
async function expectSvgHealthy(page, prefix) {
  const tongue = page.locator(`#${prefix}-tongue`);
  await expect(tongue).toBeAttached();
  const tongueD = await tongue.getAttribute('d');
  if (tongueD === null || tongueD.trim() === '') {
    throw new Error(`#${prefix}-tongue d attribute is empty — renderer is broken`);
  }

  const glottisHole = page.locator(`#${prefix}-glottis-hole`);
  await expect(glottisHole).toBeAttached();
  const glottisPts = await glottisHole.getAttribute('points');
  if (glottisPts === null || glottisPts.trim() === '') {
    throw new Error(`#${prefix}-glottis-hole points attribute is empty — renderer is broken`);
  }

  const jawGroup = page.locator(`#${prefix}-jaw-group`);
  await expect(jawGroup).toBeAttached();
  const jawTransform = await jawGroup.getAttribute('transform');
  if (jawTransform === null || jawTransform.trim() === '') {
    throw new Error(`#${prefix}-jaw-group transform is empty — renderer is broken`);
  }
}

/**
 * Wait for the analysis progress container to disappear (analysis completed).
 * Falls back to a fixed timeout if SSE/progress logic isn't wired.
 * @param {import('@playwright/test').Page} page
 * @param {number} timeoutMs
 */
async function waitForAnalysisDone(page, timeoutMs = 30000) {
  // Wait for progress to become hidden (or disappear) as the primary signal
  try {
    await page.locator('#progress-container').waitFor({ state: 'hidden', timeout: timeoutMs });
  } catch {
    // Fallback: wait for the feedback container to contain something
    await page.locator('#feedback-container > *').first().waitFor({ state: 'attached', timeout: 5000 });
  }
}

const { expect } = require('@playwright/test');

module.exports = {
  openHome,
  switchToTab,
  waitForSvgRenderer,
  expectSvgHealthy,
  waitForAnalysisDone,
};
