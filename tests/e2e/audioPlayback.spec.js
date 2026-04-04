/**
 * @deprecated Use tests/e2e/real/analysis.spec.js and
 *            tests/e2e/mocked/analysis.spec.js instead.
 *
 * Legacy placeholder — kept as a stub so existing CI pipelines
 * that reference this file don't break during migration.
 */
const { test, expect } = require('@playwright/test');

test.describe('Recording UI (legacy — see new spec files)', () => {
  test('recorder section is present in the DOM', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // smoke check — real recorder UI coverage is now in mocked/analysis.spec.js
    const recorder = page.locator('#recorder');
    await expect(recorder).toBeAttached();
  });
});
