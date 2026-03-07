import { test, expect } from '@playwright/test';

test.describe('Dashboard (Pipeline Health)', () => {
  const consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors.length = 0;
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
  });

  test('loads with heading and KPI cards', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // KPI cards render as rounded-lg bordered divs with uppercase labels
    // Look for known KPI label text that appears on the dashboard
    const kpiLabel = page.locator('text=ACTIVE POSTINGS, text=Active Postings, text=PIPELINE, text=Pipeline');
    await expect(kpiLabel.first()).toBeVisible({ timeout: 10000 });
  });

  test('renders chart area', async ({ page }) => {
    await page.goto('/');
    // Wait for Tremor/Recharts SVG or the chart container
    const chart = page.locator('svg.recharts-surface, canvas, [class*="tremor"], [class*="recharts"]');
    await expect(chart.first()).toBeVisible({ timeout: 15000 });
  });

  test('no console errors', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Filter out known benign errors (e.g., failed API calls in CI)
    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('Failed to fetch') && !e.includes('NetworkError') && !e.includes('ERR_CONNECTION')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
