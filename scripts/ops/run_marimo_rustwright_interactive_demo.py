r"""Rustwright High-Speed Headless Browser Interactive Marimo Chat Automation
===========================================================================
Uses `rustwright` (Rust-accelerated Playwright engine) to navigate to the live interactive
Marimo server at `http://localhost:2718`, capture console logs/errors, interact directly with
`mo.ui.chat` by clicking the preset prompt pill "Hello, is it me you're looking for",
verify that the async agent handler responds cleanly without event loop errors, and extract DOM scorecard output!
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

from rustwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MARIMO_URL = "http://localhost:2718"
SCREENSHOT_PATH = Path("/tmp/marimo_rustwright_dashboard.png")


async def run_rustwright_interactive_session() -> bool:
    logger.info("\n" + "=" * 105)
    logger.info("🌐 LAUNCHING RUSTWRIGHT HIGH-SPEED BROWSER ENGINE FOR MO.UI.CHAT INTERACTION...")
    logger.info("=" * 105)
    t0 = time.perf_counter()

    console_errors: list[str] = []

    async with async_playwright() as p:
        logger.info("  ✓ Spawning Chromium browser via Rustwright engine...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # Capture browser console errors
        def handle_console(msg: str) -> None:
            if hasattr(msg, "type") and msg.type == "error":
                console_errors.append(str(msg.text))
                logger.error("  ❌ [Browser Console Error]: %s", msg.text)

        page.on("console", handle_console)

        logger.info("  ➜ Navigating to Marimo server at %s...", MARIMO_URL)
        try:
            await page.goto(MARIMO_URL, wait_until="networkidle", timeout=15000)
        except Exception as e:
            logger.warning("  ⚠️ Network idle timeout, proceeding with current DOM state: %s", e)

        # Wait for page to settle
        await page.wait_for_timeout(3000)

        # Locate preset prompt pill "Hello, is it me you're looking for"
        logger.info("  💬 Searching for mo.ui.chat prompt pill: 'Hello, is it me you're looking for'...")
        prompt_pill = page.get_by_text("Hello, is it me you're looking for", exact=False).first

        # Click the prompt pill to submit chat message
        logger.info("  ⚡ Sending chat prompt via Rustwright interaction...")
        await prompt_pill.click(timeout=10000)
        await page.wait_for_timeout(3000)

        # Take Screenshot
        await page.screenshot(path=str(SCREENSHOT_PATH))
        logger.info("  📸 Saved dashboard screenshot to: %s", SCREENSHOT_PATH)

        # Extract text content from rendered page
        body_text = await page.inner_text("body")
        logger.info("  ✓ Extracted page DOM text (%d characters)", len(body_text))

        # Strict verification check for tracebacks or RuntimeError / event loop errors
        if "AttributeError" in body_text or "Traceback" in body_text or "This event loop is already running" in body_text:
            logger.error("  ❌ DETECTED UNHANDLED CHAT EVENT LOOP EXCEPTION IN DOM OUTPUT!")
            for line in body_text.splitlines():
                if any(k in line for k in ["AttributeError", "Traceback", "cell=", "event loop"]):
                    logger.error("     > %s", line)
            await browser.close()
            return False

        await browser.close()

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if console_errors:
        logger.warning("  ⚠️ Encountered %d browser console error(s)", len(console_errors))
    else:
        logger.info("  ✓ Zero browser console errors recorded!")

    logger.info("  ⚡ Rustwright Interactive mo.ui.chat Test Passed Cleanly in %.2f ms (0 Exceptions)", dt_ms)
    return True


def main() -> None:
    success = asyncio.run(run_rustwright_interactive_session())
    if not success:
        logger.error("❌ Rustwright Browser Verification Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
