import { test, expect } from '@playwright/test';

test.describe('A2UI Demo Page', () => {
  test('catalog validates successfully', async ({ page }) => {
    await page.goto('/a2ui-demo');
    await page.waitForTimeout(3000);

    // Validation badge should show PASSED
    await expect(page.locator('text=Catalog validation: PASSED')).toBeVisible();
    await expect(page.locator('text=Components: 8')).toBeVisible();
    await expect(page.locator('text=Scenes: 5')).toBeVisible();
  });

  test('void scene renders with correct components', async ({ page }) => {
    await page.goto('/a2ui-demo');
    await page.waitForTimeout(3000);

    // Void sphere button should be present
    await expect(
      page.locator('button[aria-label="Click the void to begin the cosmogony"]')
    ).toBeVisible();

    // Narration text should show void quote
    await expect(page.locator('text=In the beginning, there was nothing')).toBeVisible();

    // Inspection state should contain "currentScene": "void"
    const inspectionText = await page.locator('text="currentScene"').first().textContent();
    expect(inspectionText).toContain('"void"');
  });

  test('clicking void transitions to explosion scene', async ({ page }) => {
    await page.goto('/a2ui-demo');
    await page.waitForTimeout(3000);

    // Click the void button
    await page.locator('button[aria-label="Click the void to begin the cosmogony"]').click();
    await page.waitForTimeout(500);

    // Explosion components should appear
    await expect(page.locator('text=[Particles: exploding]')).toBeVisible();

    // Narration should update to SO(12) text
    await expect(
      page.locator('text=From the first observation, symmetry crystallized')
    ).toBeVisible();

    // Action log should show void_click
    await expect(page.locator('text=void_click')).toBeVisible();

    // Inspection state should show explosion scene
    const inspectionEl = page.locator('[class*="text-gray-400"]').filter({ hasText: '"currentScene"' }).first();
    const text = await inspectionEl.textContent();
    expect(text).toContain('"explosion"');
  });

  test('auto-transitions complete the full chain to HIHO', async ({ page }) => {
    test.setTimeout(30000); // Extended timeout for 12s animation

    await page.goto('/a2ui-demo');
    await page.waitForTimeout(3000);

    // Click void to start the chain
    await page.locator('button[aria-label="Click the void to begin the cosmogony"]').click();

    // Wait for full chain: explosion(2s) + differentiation(3s) + settling(5s) + buffer
    await page.waitForTimeout(12000);

    // Should be on HIHO scene now
    await expect(page.locator('text=[Cosmogony]')).toBeVisible();

    // Temperature slider should be present
    await expect(page.locator('input[type="range"]')).toBeVisible();

    // Inspection state should show hiho
    const inspectionEl = page.locator('[class*="text-gray-400"]').filter({ hasText: '"currentScene"' }).first();
    const text = await inspectionEl.textContent();
    expect(text).toContain('"hiho"');
  });
});
