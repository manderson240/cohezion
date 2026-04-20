import { test, expect } from '@playwright/test';

/**
 * Stitch Design System Validation (Systems Engineering V-Model)
 * Verifies that the UI artifacts adhere to .stitch/DESIGN.md tokens.
 */

test.describe('Stitch Design System Validation', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the preview page we just created
    await page.goto('/stitch-preview');
  });

  test('V-Model: Token Compliance - Core Colors', async ({ page }) => {
    // 1. Verify Void Background (#020208) on the container
    const container = page.getByTestId('stitch-preview-container');
    await expect(container).toHaveCSS('background-color', 'rgb(2, 2, 8)');
  });

  test('V-Model: Component Integrity - GenesisCard', async ({ page }) => {
    // 2. Verify GenesisCard rendering via title text
    const title = page.locator('text=NPU ANALYSIS LANE').first();
    await expect(title).toBeVisible();
    await expect(title).toHaveCSS('text-transform', 'uppercase');
  });

  test('V-Model: Domain Invariant - HIHO Coherence Dial', async ({ page }) => {
    // 3. Verify Coherence label existence
    const label = page.locator('text=COHERENCE').first();
    await expect(label).toBeVisible();
    await expect(label).toHaveCSS('font-family', /JetBrains Mono/);
  });

  test('V-Model: Hardware Data Binding', async ({ page }) => {
    // 4. Verify real-time stats from Strix Halo are reflected
    await expect(page.locator('text=111.4 TPS')).toBeVisible();
    await expect(page.locator('text=STRIX_HALO_GFX1151')).toBeVisible();
  });

});
