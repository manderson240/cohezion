#!/usr/bin/env python3
"""Capture high-resolution viewport screenshot of live Marimo WASM dashboard."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def capture_dashboard_screenshot() -> str:
    output_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/marimo_wasm_live_screenshot.png")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Standard 1080p desktop viewport
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("Navigating to http://localhost:8082/cohezion_master_dashboard_wasm.html...")
        await page.goto("http://localhost:8082/cohezion_master_dashboard_wasm.html", wait_until="domcontentloaded")

        # Give Pyodide and WebGL 8 seconds to mount the 3D surface plot
        print("Waiting for Pyodide, Plotly WebGL, and UI sliders to mount...")
        await asyncio.sleep(8)

        await page.screenshot(path=str(output_path), full_page=True)
        print(f"Screenshot successfully saved to: {output_path} ({output_path.stat().st_size} bytes)")
        await browser.close()
    return str(output_path)


if __name__ == "__main__":
    asyncio.run(capture_dashboard_screenshot())
