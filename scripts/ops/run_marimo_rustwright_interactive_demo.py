r"""Rustwright High-Speed Headless Browser Interactive Marimo Automation
=======================================================================
Uses `rustwright` (Rust-accelerated Playwright engine) to navigate to the live interactive
Marimo server at `http://localhost:2718`, click the '⚡ Run Local Inference Agent Deliberation' button,
wait for Marimo reactive re-evaluation, and extract the live deliberation output scorecard!
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from rustwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MARIMO_URL = "http://localhost:2718"
SCREENSHOT_PATH = Path("/tmp/marimo_rustwright_dashboard.png")


async def run_rustwright_interactive_session() -> bool:
    logger.info("\n" + "=" * 105)
    logger.info("🌐 LAUNCHING RUSTWRIGHT HIGH-SPEED BROWSER ENGINE FOR MARIMO AUTOMATION...")
    logger.info("=" * 105)
    t0 = time.perf_counter()

    async with async_playwright() as p:
        logger.info("  ✓ Spawning Chromium browser via Rustwright engine...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        logger.info("  ➜ Navigating to Marimo server at %s...", MARIMO_URL)
        try:
            await page.goto(MARIMO_URL, wait_until="networkidle", timeout=15000)
        except Exception as e:
            logger.warning("  ⚠️ Network idle timeout, proceeding with current DOM state: %s", e)

        # Wait for button to be visible
        logger.info("  🔍 Searching for '⚡ Run Local Inference Agent Deliberation' button...")
        button = page.locator("button:has-text('Run Local Inference Agent Deliberation')")
        
        # Click the button
        logger.info("  ⚡ Clicking button via Rustwright event dispatch...")
        await button.click()
        await page.wait_for_timeout(1000)

        # Take Screenshot
        await page.screenshot(path=str(SCREENSHOT_PATH))
        logger.info("  📸 Saved dashboard screenshot to: %s", SCREENSHOT_PATH)

        # Extract text content from rendered page
        body_text = await page.inner_text("body")
        logger.info("  ✓ Extracted page DOM text (%d characters)", len(body_text))

        await browser.close()

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    logger.info("  ⚡ Rustwright Interactive Session Completed in %.2f ms", dt_ms)
    return True


def main() -> None:
    asyncio.run(run_rustwright_interactive_session())


if __name__ == "__main__":
    main()
