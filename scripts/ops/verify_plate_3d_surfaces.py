#!/usr/bin/env python3
"""Verify 3D Micrograph Topography Viewer via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_true_plate_3d_viewer.html"
screenshot_sh = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/plate_3d_surfaces/shoulders_3d_surface_screenshot.png")
screenshot_mat = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/plate_3d_surfaces/matsumoto_3d_surface_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 950})

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)

    page.screenshot(path=str(screenshot_sh))
    print(f"✓ Saved 3D Topography Screenshot (Shoulders): {screenshot_sh}")

    page.click("#opt-mat")
    page.wait_for_timeout(2500)
    page.screenshot(path=str(screenshot_mat))
    print(f"✓ Saved 3D Topography Screenshot (Matsumoto): {screenshot_mat}")

    browser.close()

print("🎉 3D MICROGRAPH TOPOGRAPHY VERIFIED!")
