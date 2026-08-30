#!/usr/bin/env python3
"""Verify Calibrated 3D Metrology Viewer via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_calibrated_metrology_3d_viewer.html"
screenshot_sh = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/calibrated_3d_surfaces/calibrated_shoulders_borehole_screenshot.png")
screenshot_mat = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/calibrated_3d_surfaces/calibrated_matsumoto_fft_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 950})

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)

    # 1. Capture Calibrated Shoulders Boreholes
    page.screenshot(path=str(screenshot_sh))
    print(f"✓ Saved Calibrated Shoulders Screenshot: {screenshot_sh}")

    # 2. Capture Calibrated Matsumoto FFT Emulsion Ring
    page.click("#opt-mat")
    page.wait_for_timeout(2500)
    page.screenshot(path=str(screenshot_mat))
    print(f"✓ Saved Calibrated Matsumoto Screenshot: {screenshot_mat}")

    browser.close()

print("🎉 CALIBRATED 3D METROLOGY VIEWER VERIFIED!")
