import { test, expect } from '@playwright/test';

test.describe('Anima Dashboard Core Functionality', () => {
  test('should load the dashboard and display the main layout', async ({ page }) => {
    // 1. Navigate to the base URL
    await page.goto('/');

    // 2. Main title exists
    await expect(page.locator('text=COHEZION')).toBeVisible();

    // 3. Check for specific UI elements
    await expect(page.locator('text=Swarm')).toBeVisible();
    await expect(page.locator('text=Flume')).toBeVisible();

    // 4. Check if the three.js visualization container exists
    const canvasContainer = page.locator('.threejs-container');
    if (await canvasContainer.count() > 0) {
      await expect(canvasContainer).toBeVisible();
    }
  });

  test('should navigate to the Flume interface', async ({ page }) => {
    await page.goto('/');
    // Click the FLUME nav or button
    const flumeButton = page.locator('a', { hasText: /flume/i }).first();
    if (await flumeButton.count() > 0) {
      await flumeButton.click();
      await expect(page).toHaveURL(/.*flume/);
      await expect(page.locator('text=Encoder')).toBeVisible();
    }
  });
});
