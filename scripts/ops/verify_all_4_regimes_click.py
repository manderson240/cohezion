#!/usr/bin/env python3
"""Automated click and render test for all 4 regimes with exact browser console error logging."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def test_all_regimes() -> None:
    screenshot_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 950})

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGE_ERROR] {err}"))

        await page.goto("http://localhost:8082/cohezion_master_dashboard_wasm.html", wait_until="domcontentloaded")
        await asyncio.sleep(8)

        # Regimes to test
        regimes = [
            ("regime_1_shoulders_toroid.png", "Shoulders Primary Toroidal EVO Core"),
            ("regime_2_string_of_pearls.png", "Shoulders 'String-of-Pearls' Multi-Vortex Chain"),
            ("regime_3_matsumoto_filaments.png", "Matsumoto Helical Filament & Nuclear Track"),
            ("regime_4_cathode_crater.png", "Target Cathode Micro-Crater Borehole Strike"),
        ]

        select_elem = page.locator('select').first
        for file_name, label in regimes:
            print(f"Testing regime: {label}...")
            await select_elem.select_option(label=label)
            await asyncio.sleep(2)
            await page.screenshot(path=str(screenshot_dir / file_name), full_page=True)
            print(f"  ✓ Captured {file_name}")

        print("\n--- CONSOLE LOGS CAPTURED ---")
        for log in console_logs:
            if "STDERR" in log or "exception" in log or "Error" in log:
                print(log)
        print("-----------------------------\n")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_all_regimes())
