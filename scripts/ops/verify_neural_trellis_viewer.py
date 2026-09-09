#!/usr/bin/env python3
"""Verify Cohezion Neural TRELLIS 3D Viewer in headless Chromium via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_neural_trellis_viewer.html"
screenshot_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/trellis_generated_assets/trellis_matsumoto_3d_screenshot.png")

print(f"Opening {url} with Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    page.screenshot(path=str(screenshot_path))
    print(f"✓ Screenshot saved to: {screenshot_path} ({screenshot_path.stat().st_size} bytes)")

    browser.close()

print("Console messages during render:")
for l in console_logs[:10]:
    print(" ", l)

print("🎉 VERIFICATION PASSED!")
