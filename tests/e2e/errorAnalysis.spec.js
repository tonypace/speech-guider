/**
 * @deprecated Use tests/e2e/real/analysis.spec.js and
 *            tests/e2e/mocked/analysis.spec.js instead.
 *
 * Legacy placeholder — kept as a stub so existing CI pipelines
 * that reference this file don't break during migration.
 */
const { test, expect } = require('@playwright/test');

test.describe('Error Analysis UI (legacy — see new spec files)', () => {
  test('error list section is present in the DOM', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // smoke check — real error analysis coverage is now in
    // tests/e2e/real/analysis.spec.js and mocked/analysis.spec.js
    const errorList = page.locator('#error-list');
    await expect(errorList).toBeAttached();
  });
});
