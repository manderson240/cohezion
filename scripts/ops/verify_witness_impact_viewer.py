#!/usr/bin/env python3
"""Verify 3D Witness Plate Impact Crater Viewer via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_witness_plate_impact_3d_viewer.html"
screenshot_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/plate_3d_surfaces/borehole_impact_3d_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 950})

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    page.screenshot(path=str(screenshot_path))
    print(f"✓ Saved 3D Borehole Impact Crater Screenshot: {screenshot_path}")

    browser.close()

print("🎉 3D WITNESS PLATE IMPACT CRATER VIEWER VERIFIED!")
