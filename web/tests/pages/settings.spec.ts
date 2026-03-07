import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('pipeline controls are visible', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Look for pipeline control buttons
    const controls = page.locator('button:has-text("Start"), button:has-text("Stop"), button:has-text("Pause"), button:has-text("Run")');
    await expect(controls.first()).toBeVisible({ timeout: 10000 });
  });

  test('run history section renders', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Look for run history table or list
    const history = page.locator('table, [class*="history"], [class*="run"]');
    await expect(history.first()).toBeVisible({ timeout: 10000 });
  });
});
