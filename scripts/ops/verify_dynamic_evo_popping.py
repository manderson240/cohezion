#!/usr/bin/env python3
"""Automated verification of dynamic EVO birth/death popping animations."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def test_dynamic_evos() -> None:
    screenshot_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 950})

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        await page.goto("http://localhost:8082/cohezion_evo_standalone_viewer.html", wait_until="domcontentloaded")

        # Capture initial state
        await asyncio.sleep(2)
        await page.screenshot(path=str(screenshot_dir / "evo_dynamic_pop_state_1.png"), full_page=True)
        print("  ✓ Captured dynamic state 1")

        # Wait 3 seconds for stochastic births and deaths to occur
        await asyncio.sleep(3)
        await page.screenshot(path=str(screenshot_dir / "evo_dynamic_pop_state_2.png"), full_page=True)
        print("  ✓ Captured dynamic state 2 (post-nucleation/decay)")

        # Trigger high-voltage discharge burst
        await page.click('button.btn-danger')
        await asyncio.sleep(1)
        await page.screenshot(path=str(screenshot_dir / "evo_dynamic_burst.png"), full_page=True)
        print("  ✓ Captured dynamic state 3 (burst injected)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_dynamic_evos())
