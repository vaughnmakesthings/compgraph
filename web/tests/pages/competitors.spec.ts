import { test, expect } from '@playwright/test';

test.describe('Competitors', () => {
  test('list page loads with heading', async ({ page }) => {
    await page.goto('/competitors');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('competitor cards or list items render', async ({ page }) => {
    await page.goto('/competitors');
    // Wait for content to load (skeleton should clear)
    await page.waitForLoadState('networkidle');
    const items = page.locator('a[href*="/competitors/"]');
    await expect(items.first()).toBeVisible({ timeout: 10000 });
  });

  test('click navigates to dossier and back', async ({ page }) => {
    await page.goto('/competitors');
    await page.waitForLoadState('networkidle');
    const firstLink = page.locator('a[href*="/competitors/"]').first();
    await expect(firstLink).toBeVisible({ timeout: 10000 });
    await firstLink.click();

    // Should navigate to a dossier page
    await expect(page).toHaveURL(/\/competitors\/.+/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Navigate back
    await page.goBack();
    await expect(page).toHaveURL(/\/competitors$/);
  });
});
