import { test, expect } from '@playwright/test';

test.describe('A2UI Demo Page', () => {
  test('catalog validates successfully', async ({ page }) => {
    await page.goto('/a2ui-demo');
    // Wait for the A2UI renderer to hydrate (data-a2ui-scene attribute appears)
    await page.waitForSelector('[data-a2ui-scene]', { timeout: 10000 });

    await expect(page.locator('text=Catalog validation: PASSED')).toBeVisible();
    await expect(page.locator('text=Components: 8')).toBeVisible();
    await expect(page.locator('text=Scenes: 5')).toBeVisible();
  });

  test('void scene renders with correct components', async ({ page }) => {
    await page.goto('/a2ui-demo');
    await page.waitForSelector('[data-a2ui-scene="void"]', { timeout: 10000 });

    // Void sphere button (check by data attribute, more reliable than aria-label)
    await expect(page.locator('[data-a2ui-component="cohezion-void-sphere"]')).toBeVisible();

    // Narration text
    await expect(page.locator('text=In the beginning, there was nothing')).toBeVisible();

    // Inspection state contains void scene
    const inspectionText = await page.locator('pre').first().textContent();
    expect(inspectionText).toContain('"currentScene"');
    expect(inspectionText).toContain('"void"');
  });

  test('clicking void transitions to explosion scene', async ({ page }) => {
    await page.goto('/a2ui-demo');
    await page.waitForSelector('[data-a2ui-component="cohezion-void-sphere"]', { timeout: 10000 });

    // Click the void sphere component
    await page.locator('[data-a2ui-component="cohezion-void-sphere"]').click();
    await page.waitForTimeout(500);

    // Explosion components should appear
    await expect(page.locator('[data-a2ui-component="cohezion-explosion"]')).toBeVisible();

    // Narration should update to SO(12) text
    await expect(
      page.locator('text=From the first observation, symmetry crystallized')
    ).toBeVisible();

    // Action log should show void_click
    await expect(page.locator('text=void_click')).toBeVisible();
  });

  test('auto-transitions complete the full chain to HIHO', async ({ page }) => {
    test.setTimeout(30000);

    await page.goto('/a2ui-demo');
    await page.waitForSelector('[data-a2ui-component="cohezion-void-sphere"]', { timeout: 10000 });

    // Click void to start the chain
    await page.locator('[data-a2ui-component="cohezion-void-sphere"]').click();

    // Wait for full chain: explosion(2s) + differentiation(3s) + settling(5s) + buffer
    await page.waitForSelector('[data-a2ui-component="cohezion-equation-panel"]', { timeout: 15000 });

    // Temperature slider should be present
    await expect(page.locator('input[type="range"]')).toBeVisible();

    // Inspection state should show hiho
    const inspectionText = await page.locator('pre').first().textContent();
    expect(inspectionText).toContain('"hiho"');
  });
});
