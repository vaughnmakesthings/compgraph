import { test, expect } from '@playwright/test';

test.describe('Hiring (Job Feed)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/hiring');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('job feed table or list renders', async ({ page }) => {
    await page.goto('/hiring');
    await page.waitForLoadState('networkidle');
    // Look for table rows or list items
    const content = page.locator('table tbody tr, [class*="ag-row"], [role="row"]');
    await expect(content.first()).toBeVisible({ timeout: 15000 });
  });

  test('filter controls are present', async ({ page }) => {
    await page.goto('/hiring');
    // Look for filter elements — select dropdowns, search inputs, or filter buttons
    const filters = page.locator('select, input[type="search"], input[placeholder*="earch"], [role="combobox"], button:has-text("Filter")');
    await expect(filters.first()).toBeVisible({ timeout: 10000 });
  });
});
