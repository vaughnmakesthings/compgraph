import { test, expect } from '@playwright/test';

test.describe('Hiring (Job Feed)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/hiring');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('job feed table or list renders', async ({ page }) => {
    await page.goto('/hiring');
    await page.waitForLoadState('networkidle');
    // Look for table rows, AG Grid rows, or a "no results" fallback
    const content = page.locator('table tbody tr, [class*="ag-row"], [role="row"], text=No postings');
    await expect(content.first()).toBeVisible({ timeout: 15000 });
  });

  test('filter controls are present', async ({ page }) => {
    await page.goto('/hiring');
    // Hiring page uses native <select> dropdowns for filtering
    const filters = page.locator('select');
    await expect(filters.first()).toBeVisible({ timeout: 10000 });
  });
});
