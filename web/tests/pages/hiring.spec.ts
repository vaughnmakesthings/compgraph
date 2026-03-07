import { test, expect } from '@playwright/test';

test.describe('Hiring (Job Feed)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/hiring');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('page renders content area', async ({ page }) => {
    await page.goto('/hiring');
    await page.waitForLoadState('networkidle');
    // Page should show either data table, "no results" message, or error state
    const content = page.locator('table, [role="alert"], select, text=No postings, text=Loading');
    await expect(content.first()).toBeVisible({ timeout: 15000 });
  });

  test('filter controls are present', async ({ page }) => {
    await page.goto('/hiring');
    // Hiring page renders <select> dropdowns regardless of data state
    const filters = page.locator('select');
    await expect(filters.first()).toBeVisible({ timeout: 10000 });
  });
});
