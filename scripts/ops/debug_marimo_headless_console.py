#!/usr/bin/env python3
"""Debug Marimo in Headless Browser to capture exact Browser Console Error."""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def inspect_browser_console() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[PAGE_ERROR] {err}"))

        print("Navigating to http://localhost:8082/cohezion_master_dashboard_wasm.html...")
        try:
            # Wait for domcontentloaded rather than full networkidle to avoid hanging on open websocket/streams
            await page.goto("http://localhost:8082/cohezion_master_dashboard_wasm.html", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(10)  # Wait for Pyodide worker to run
        except Exception as e:
            print(f"Navigation error: {e}")

        print("\n--- BROWSER CONSOLE LOGS ---")
        for log in console_logs:
            print(log)
        print("----------------------------\n")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_browser_console())
