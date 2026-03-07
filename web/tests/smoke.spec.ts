import { test, expect } from '@playwright/test';

test.describe('Smoke', () => {
  test('backend health returns 200', async ({ request }) => {
    const base = process.env.NEXT_PUBLIC_API_URL || 'https://dev.compgraph.io';
    const res = await request.get(`${base}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });

  test('frontend loads', async ({ page }) => {
    const res = await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 20000 });
    expect(res?.status()).toBe(200);
  });
});
