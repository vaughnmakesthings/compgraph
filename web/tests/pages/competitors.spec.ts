import { test, expect } from '@playwright/test';

test.describe('Competitors', () => {
  test('list page loads with heading', async ({ page }) => {
    await page.goto('/competitors');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText('Competitors')).toBeVisible();
  });

  test('page renders content or error state', async ({ page }) => {
    await page.goto('/competitors');
    await page.waitForLoadState('networkidle');
    // Page should show either competitor cards, loading state, or error alert
    const content = page.locator(
      'button[aria-label*="details"], [role="alert"], text=Field marketing agencies'
    );
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });

  test('subtitle text is visible', async ({ page }) => {
    await page.goto('/competitors');
    // The subtitle always renders regardless of data state
    await expect(
      page.getByText('Field marketing agencies in our competitive set')
    ).toBeVisible({ timeout: 10000 });
  });
});
