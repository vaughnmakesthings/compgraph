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

    // KPI cards should render (look for stat values or card containers)
    const cards = page.locator('[class*="kpi"], [class*="stat"], [class*="card"]');
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test('renders chart area', async ({ page }) => {
    await page.goto('/');
    // Wait for any chart SVG or canvas to appear
    const chart = page.locator('svg.recharts-surface, canvas, [class*="chart"]');
    await expect(chart.first()).toBeVisible({ timeout: 10000 });
  });

  test('no console errors', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    expect(consoleErrors).toHaveLength(0);
  });
});
