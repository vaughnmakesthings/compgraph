import { test, expect } from '@playwright/test';

test.describe('Dashboard (Pipeline Health)', () => {
  test('loads with heading', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('renders main content area', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Dashboard shows either KPI data, a loading skeleton, or an error alert
    const content = page.locator('[role="alert"], svg.recharts-surface, [class*="tremor"], [class*="skeleton"], [aria-busy="true"]');
    // At minimum the page should have rendered *something* beyond the heading
    const mainContent = page.locator('main, [role="main"]').or(page.locator('.flex-1'));
    await expect(mainContent.first()).toBeVisible({ timeout: 10000 });
  });

  test('no critical console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Filter out expected network errors (API may not be reachable in CI)
    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('Failed to fetch') &&
        !e.includes('NetworkError') &&
        !e.includes('ERR_CONNECTION') &&
        !e.includes('net::') &&
        !e.includes('ECONNREFUSED') &&
        !e.includes('TypeError: fetch failed') &&
        !e.includes('Load failed')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
