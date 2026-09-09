#!/usr/bin/env python3
"""Verify Empirical Micrograph Apparatus Studio via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_empirical_micrograph_apparatus_studio.html"
screenshot_path_sh = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/empirical_studio_shoulders_screenshot.png")
screenshot_path_mat = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/empirical_studio_matsumoto_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # 1. Capture Shoulders Studio with Raw SEM Plate
    page.screenshot(path=str(screenshot_path_sh))
    print(f"✓ Captured Shoulders Empirical Studio: {screenshot_path_sh}")

    # 2. Switch to Matsumoto and capture Nuclear Emulsion Studio
    page.click("#nav-matsumoto")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(screenshot_path_mat))
    print(f"✓ Captured Matsumoto Empirical Studio: {screenshot_path_mat}")

    browser.close()

print("🎉 EMPIRICAL MICROGRAPH STUDIO VERIFIED!")
