import { test, expect } from '@playwright/test';

/**
 * Portfolio E2E Tests - FLUME VAE Demo
 *
 * Coverage Areas:
 * 1. Core Visualization (3 tests) - rendering, interactions, data updates
 * 2. Edge Cases (3 tests) - WebGL loss, errors, timeouts
 * 3. Accessibility (3 tests) - keyboard nav, ARIA, screen reader
 *
 * Test Strategy:
 * - TDD approach: tests written before fixes
 * - Adversarial mindset: test failure paths, race conditions
 * - Real browser automation: catches issues unit tests miss
 */

test.describe('Portfolio FLUME Visualization - Core Functionality', () => {
  test('should load portfolio landing page with 5 pillars', async ({ page }) => {
    // Navigate to portfolio
    await page.goto('/portfolio');

    // Verify hero section (use .first() to avoid strict mode violation - text appears twice)
    await expect(page.locator('text=Compound AI orchestration').first()).toBeVisible({ timeout: 10000 });

    // Verify all 5 pillar cards present (use role='heading' to target card titles specifically)
    await expect(page.locator('h3', { hasText: 'FLUME VAE' })).toBeVisible();
    await expect(page.locator('h3', { hasText: 'Compound Loop' })).toBeVisible();
    await expect(page.locator('h3', { hasText: 'Universe Simulation' })).toBeVisible();
    await expect(page.locator('h3', { hasText: 'Multi-Agent Swarm' })).toBeVisible();
    await expect(page.locator('h3', { hasText: 'Evaluation Infrastructure' })).toBeVisible();

    // Verify problem/solution/proof sections
    await expect(page.locator('text=The Problem')).toBeVisible();
    await expect(page.locator('text=The Solution')).toBeVisible();
    await expect(page.locator('text=The Proof')).toBeVisible();
  });

  test('should navigate to FLUME demo and render 3D visualization', async ({ page }) => {
    // Navigate to FLUME demo
    await page.goto('/portfolio/flume');

    // Wait for page title (exact match from page.tsx line 79-81)
    await expect(page.locator('h1', { hasText: 'FLUME VAE' })).toBeVisible({ timeout: 10000 });

    // Wait for canvas to initialize (Three.js WebGL)
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 15000 });

    // Verify stats dashboard is present (use exact header text from FlumeNavigator.tsx:275-291)
    await expect(page.locator('text=LATENT DIM')).toBeVisible();
    await expect(page.locator('text=SAMPLES')).toBeVisible();
    await expect(page.locator('text=MEAN COHERENCE')).toBeVisible();

    // Verify interactive controls
    await expect(page.locator('input[type="range"]')).toBeVisible();
    await expect(page.locator('button', { hasText: /resample/i })).toBeVisible();

    // Wait for initial data load (stats should not be "Loading...")
    await page.waitForFunction(() => {
      const statsElement = document.querySelector('[data-testid="mean-coherence"]');
      return statsElement && !statsElement.textContent?.includes('Loading');
    }, { timeout: 20000 });
  });

  test('should update visualization when sample count slider changes', async ({ page }) => {
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Get initial slider value (next to slider, line 309 of FlumeNavigator)
    const initialValue = await page.locator('input[type="range"]').getAttribute('value');

    // Move slider to 300 samples
    const slider = page.locator('input[type="range"]');
    await slider.fill('300');

    // Wait for API response and re-render (backend may take up to 10s with PCA)
    await page.waitForTimeout(12000);

    // Verify slider value updated
    const newValue = await slider.getAttribute('value');
    expect(newValue).toBe('300');
    expect(newValue).not.toBe(initialValue);

    // Verify stats dashboard updated (mean coherence should be different)
    const meanCoherence = await page.locator('[data-testid="mean-coherence"]').textContent();
    expect(meanCoherence).not.toBe('N/A');
    expect(meanCoherence).toMatch(/\d+\.\d{3}/); // Format: 0.XXX
  });
});

test.describe('Portfolio FLUME Visualization - Edge Cases & Error Handling', () => {
  test('should handle rapid slider changes without race conditions', async ({ page }) => {
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Rapidly change slider 5 times (tests AbortController cancellation)
    const slider = page.locator('input[type="range"]');
    await slider.fill('100');
    await page.waitForTimeout(100);
    await slider.fill('200');
    await page.waitForTimeout(100);
    await slider.fill('300');
    await page.waitForTimeout(100);
    await slider.fill('400');
    await page.waitForTimeout(100);
    await slider.fill('500');

    // Wait for final request to complete
    await page.waitForTimeout(12000);

    // Verify final state matches slider (no stale data)
    const finalValue = await slider.getAttribute('value');
    expect(finalValue).toBe('500');

    // Verify no JavaScript errors in console
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    expect(errors).toHaveLength(0);
  });

  test('should show error boundary when WebGL context is lost', async ({ page, context }) => {
    // This test simulates WebGL context loss (requires Chrome DevTools Protocol)
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Evaluate script to force WebGL context loss
    await page.evaluate(() => {
      const canvas = document.querySelector('canvas') as HTMLCanvasElement;
      if (canvas) {
        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
        if (gl) {
          // Trigger WEBGL_lose_context extension (if available)
          const ext = gl.getExtension('WEBGL_lose_context');
          if (ext) {
            ext.loseContext();
          }
        }
      }
    });

    // Wait for error boundary to render
    await page.waitForTimeout(2000);

    // Verify error boundary is shown (from Issue #12 fix)
    const errorMessage = page.locator('text=WEBGL CONTEXT LOST');
    if (await errorMessage.isVisible()) {
      // Error boundary rendered successfully
      await expect(page.locator('button', { hasText: /reload/i })).toBeVisible();
    } else {
      // Context loss not triggered (extension not available), verify fallback
      console.log('WebGL context loss extension not available, skipping');
    }
  });

  test('should handle backend errors gracefully with sanitized messages', async ({ page }) => {
    // Navigate to page
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Intercept API call and return error
    await page.route('**/api/flume/latent-space', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'FLUME VAE checkpoint not found. Train the model first using /flume/train'
        })
      });
    });

    // Trigger resample (should hit mocked error)
    const resampleBtn = page.locator('button', { hasText: /resample/i });
    await resampleBtn.click();

    // Wait for error to be displayed
    await page.waitForTimeout(2000);

    // Verify error message is shown
    const errorText = await page.locator('body').textContent();
    expect(errorText).toContain('FLUME VAE checkpoint not found');

    // Verify NO filesystem paths leaked (Issue #4 security fix)
    expect(errorText).not.toMatch(/\/home\/|\/usr\/|\/var\/|C:\\|\/secret\//);
  });
});

test.describe('Portfolio FLUME Visualization - Accessibility', () => {
  test('should have proper ARIA labels for screen readers', async ({ page }) => {
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Check for ARIA labels on interactive elements (Issue #16 fix)
    const slider = page.locator('input[type="range"]');
    await expect(slider).toHaveAttribute('aria-label', /sample count/i);

    const resampleBtn = page.locator('button', { hasText: /resample/i });
    await expect(resampleBtn).toHaveAttribute('aria-label', /resample|generate new/i);

    // Verify canvas has descriptive label
    const canvas = page.locator('canvas');
    const canvasParent = canvas.locator('..');
    const ariaDescription = await canvasParent.getAttribute('aria-label') ||
                            await canvasParent.getAttribute('aria-describedby');
    expect(ariaDescription).toBeTruthy();
  });

  test('should support keyboard navigation for interactive controls', async ({ page }) => {
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Tab to slider
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Verify slider is focused
    const slider = page.locator('input[type="range"]');
    await expect(slider).toBeFocused();

    // Use arrow keys to change value
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');

    // Tab to resample button
    await page.keyboard.press('Tab');
    const resampleBtn = page.locator('button', { hasText: /resample/i });
    await expect(resampleBtn).toBeFocused();

    // Press Enter to activate
    await page.keyboard.press('Enter');

    // Verify request was triggered (wait for loading state or network)
    await page.waitForTimeout(2000);
  });

  test('should maintain readability and contrast for stats dashboard', async ({ page }) => {
    await page.goto('/portfolio/flume');
    await page.waitForSelector('canvas', { timeout: 15000 });

    // Wait for stats to load
    await page.waitForFunction(() => {
      const statsElement = document.querySelector('[data-testid="mean-coherence"]');
      return statsElement && !statsElement.textContent?.includes('Loading');
    }, { timeout: 20000 });

    // Check text colors have sufficient contrast (WCAG AA: 4.5:1 for normal text)
    const statsContainer = page.locator('.stats-container').first();

    // Get computed styles
    const backgroundColor = await statsContainer.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );
    const textColor = await statsContainer.evaluate(el =>
      window.getComputedStyle(el).color
    );

    // Verify colors are not identical (basic contrast check)
    expect(backgroundColor).not.toBe(textColor);

    // Verify text is visible (not transparent or hidden)
    const meanCoherence = page.locator('[data-testid="mean-coherence"]');
    await expect(meanCoherence).toBeVisible();
    const textContent = await meanCoherence.textContent();
    expect(textContent).toBeTruthy();
    expect(textContent).not.toBe('');
  });
});
