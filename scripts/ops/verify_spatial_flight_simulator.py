#!/usr/bin/env python3
"""Verify 3D EVO Spatial Flight & Popping Simulator via Playwright."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


url = "http://localhost:8082/cohezion_evo_spatial_pop_flight_simulator.html"
screenshot_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/evo_flight_pop_3d_screenshot.png")

print(f"Testing {url} in Headless Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2500)

    # Click high-voltage discharge burst
    page.click(".btn-burst")
    page.wait_for_timeout(2000)

    page.screenshot(path=str(screenshot_path))
    print(f"✓ Screenshot captured: {screenshot_path} ({screenshot_path.stat().st_size} bytes)")

    # Read active EVO count
    active_evos = page.inner_text("#stat-active-evos")
    electrons = page.inner_text("#stat-electrons")
    print(f"✓ Live Swarm Telemetry -> Active EVOs: {active_evos}, Total Charge: {electrons} electrons")

    browser.close()

print("🎉 SPATIAL FLIGHT & POPPING VERIFICATION COMPLETE!")
