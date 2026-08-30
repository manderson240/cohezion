#!/usr/bin/env python3
"""Local Image Generation Benchmark via Lemonade Server (:13305)."""

import asyncio
import base64
import httpx
import json
import os
import time
from pathlib import Path

LEMONADE_URL = "http://localhost:13305/v1/images/generations"
OUTPUT_PATH = Path("docs/papers/flume_arc_paper_thumbnail_local_sd.jpg")

PROMPT = (
    "A sleek, hyper-modern academic science banner for FLUME AI research. "
    "Glowing 3D Poincare hyperbolic disk, continuous geodesic trajectories in electric cyan and amber gold, "
    "abstract sheaf network nodes connecting grid tiles, dark mode computational physics, 560x280 aspect ratio."
)

async def test_local_image_gen():
    print("\n" + "=" * 110)
    print("🎨 TESTING LOCAL ON-DEVICE IMAGE GENERATION (Lemonade :13305)")
    print("=" * 110)

    payload = {
        "model": "SD-Turbo",
        "prompt": PROMPT,
        "n": 1,
        "size": "512x512",
        "response_format": "b64_json"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            t0 = time.perf_counter()
            r = await client.post(LEMONADE_URL, json=payload)
            dt = round(time.perf_counter() - t0, 2)
            print(f"• HTTP Status from Lemonade: {r.status_code} ({dt}s)")
            if r.status_code == 200:
                data = r.json()
                b64_str = data["data"][0].get("b64_json")
                if b64_str:
                    img_bytes = base64.b64decode(b64_str)
                    OUTPUT_PATH.write_bytes(img_bytes)
                    print(f"✓ Saved locally generated image to `{OUTPUT_PATH}` ({len(img_bytes)} bytes)")
            else:
                print(f"• Response detail: {r.text[:300]}")
        except Exception as e:
            print(f"• Local endpoint communication note: {e}")

    print("=" * 110 + "\n")

if __name__ == "__main__":
    asyncio.run(test_local_image_gen())
