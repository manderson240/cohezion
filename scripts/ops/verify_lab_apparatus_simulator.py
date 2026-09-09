#!/usr/bin/env python3
"""Verify 3D Laboratory Apparatus Simulator via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_laboratory_apparatus_simulator.html"
screenshot_path_shoulders = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/shoulders_apparatus_3d_screenshot.png")
screenshot_path_matsumoto = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/matsumoto_apparatus_3d_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # 1. Fire pulse in Shoulders Vacuum Diode
    page.click(".action-btn")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(screenshot_path_shoulders))
    print(f"✓ Captured Shoulders Apparatus Screenshot: {screenshot_path_shoulders}")

    # 2. Switch to Matsumoto Spark Cell
    page.click("#btn-matsumoto")
    page.wait_for_timeout(1500)
    page.click(".action-btn")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(screenshot_path_matsumoto))
    print(f"✓ Captured Matsumoto Apparatus Screenshot: {screenshot_path_matsumoto}")

    browser.close()

print("🎉 LABORATORY APPARATUS SIMULATION VERIFIED!")
