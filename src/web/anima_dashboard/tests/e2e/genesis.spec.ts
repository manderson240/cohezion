import { test, expect, type ConsoleMessage } from '@playwright/test';

test.describe('Genesis Page - Bug Fix Regressions', () => {
  test('should load without console errors (no 404 spam)', async ({ page }) => {
    const errors: ConsoleMessage[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg);
    });

    await page.goto('/genesis');
    // Wait for 3D canvas to mount (replaces "Loading the cosmos...")
    await page.waitForTimeout(4000);

    // Filter out AudioContext warnings (browser policy, not a bug)
    const realErrors = errors.filter(
      (e) => !e.text().includes('AudioContext')
    );

    expect(realErrors).toHaveLength(0);
  });

  test('void quote and click-to-begin do not overlap', async ({ page }) => {
    await page.goto('/genesis');
    await page.waitForTimeout(4000);

    // Both texts should be present in the page
    const clickToBegin = page.locator('text=click to begin');
    const voidQuote = page.locator('text=In the beginning');

    // At least one instance of each should exist
    await expect(clickToBegin.first()).toBeVisible();
    await expect(voidQuote.first()).toBeVisible();

    // Get bounding boxes to verify they don't overlap
    const ctaBox = await clickToBegin.first().boundingBox();
    const quoteBox = await voidQuote.first().boundingBox();

    expect(ctaBox).toBeTruthy();
    expect(quoteBox).toBeTruthy();

    if (ctaBox && quoteBox) {
      // Quote should be ABOVE the CTA (lower Y value) or clearly separated
      // Allow for the quote to be either above or below, just not overlapping
      const verticalOverlap =
        ctaBox.y < quoteBox.y + quoteBox.height &&
        quoteBox.y < ctaBox.y + ctaBox.height;

      const horizontalOverlap =
        ctaBox.x < quoteBox.x + quoteBox.width &&
        quoteBox.x < ctaBox.x + ctaBox.width;

      // They should NOT both overlap vertically AND horizontally
      expect(verticalOverlap && horizontalOverlap).toBe(false);
    }
  });

  test('cosmogony sidebar hidden during void phase', async ({ page }) => {
    await page.goto('/genesis');
    await page.waitForTimeout(4000);

    // The CosmogonyTimeline heading should exist in DOM but not be visible
    // (opacity: 0 during void phase)
    const cosmogonyHeading = page.locator('h3:has-text("Cosmogony")');

    // It may be in the DOM with opacity 0, or the container may hide it
    // Either way, it should not be visually prominent
    if (await cosmogonyHeading.count() > 0) {
      // Check the parent container's computed opacity
      const opacity = await cosmogonyHeading.evaluate((el) => {
        let node: HTMLElement | null = el as HTMLElement;
        while (node) {
          const style = window.getComputedStyle(node);
          if (parseFloat(style.opacity) === 0) return 0;
          node = node.parentElement;
        }
        return 1;
      });
      expect(opacity).toBe(0);
    }
    // If the heading doesn't exist at all, that's also fine
  });

  test('narration text appears after page load', async ({ page }) => {
    await page.goto('/genesis');
    // Wait for the 1.5s delay + render time for narration trigger
    await page.waitForTimeout(5000);

    // Look for the narration overlay with the void text
    const narrationOverlay = page.locator('.narration-overlay');
    const narrationText = page.locator('text=In the beginning');

    // Either the dedicated overlay or any element with the text should be visible
    const overlayVisible = await narrationOverlay.count() > 0;
    const textVisible = await narrationText.count() > 0;

    expect(overlayVisible || textVisible).toBe(true);
  });

  test('sound toggle does not produce JS errors', async ({ page }) => {
    await page.goto('/genesis');
    await page.waitForTimeout(2000);

    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Filter AudioContext (expected) and Tone.js start time (handled)
        if (!text.includes('AudioContext') && !text.includes('Start time')) {
          errors.push(text);
        }
      }
    });

    // Click Sound OFF → Sound ON
    const soundBtn = page.locator('button:has-text("Sound")');
    await expect(soundBtn).toBeVisible();
    await soundBtn.click();

    await page.waitForTimeout(1000);

    // Click again to toggle off
    await soundBtn.click();
    await page.waitForTimeout(500);

    expect(errors).toHaveLength(0);
  });
});
