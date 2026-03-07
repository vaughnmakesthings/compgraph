import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('pipeline controls section renders', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Pipeline Controls is a SectionCard with heading text
    await expect(page.getByText('Pipeline Controls')).toBeVisible({ timeout: 10000 });
  });

  test('run history section renders', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    // Scrape Run History is a SectionCard heading
    await expect(page.getByText('Scrape Run History')).toBeVisible({ timeout: 10000 });
  });
});
