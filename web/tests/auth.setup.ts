import { test as setup, expect } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;

  if (!email || !password) {
    throw new Error('E2E_USER_EMAIL and E2E_USER_PASSWORD env vars are required');
  }

  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /sign in|log in/i }).click();

  // Wait for redirect to dashboard (authenticated state)
  await expect(page).toHaveURL(/\/$/, { timeout: 15000 });

  await page.context().storageState({ path: 'tests/.auth/user.json' });
});
