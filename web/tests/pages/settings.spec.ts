import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('pipeline controls are visible', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Pipeline Controls section has Trigger buttons
    const controls = page.locator('button:has-text("Trigger")');
    await expect(controls.first()).toBeVisible({ timeout: 10000 });
  });

  test('run history section renders', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Look for run history heading or table, or "No runs recorded" fallback
    const history = page.locator('text=Run History, text=No runs recorded, table');
    await expect(history.first()).toBeVisible({ timeout: 10000 });
  });
});
