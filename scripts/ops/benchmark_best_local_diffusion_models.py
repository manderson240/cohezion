#!/usr/bin/env python3
"""Benchmarks the Best Available Local Diffusion Models on Lemonade (:13305).

Models tested:
1. `SDXL-Turbo` (High-res 1024x1024 / Photorealistic details)
2. `Flux-2-Klein-4B` / `Flux-2-Klein-9B-GGUF` (Frontier DiT Transformer architecture)
3. `Z-Image-Turbo` (Ultra high-contrast physics graphics)
4. `SD-Turbo` (Fast baseline)
"""

import asyncio
import base64
import httpx
import json
import time
from pathlib import Path

LEMONADE_IMAGE_URL = "http://localhost:13305/v1/images/generations"
OUTPUT_DIR = Path("docs/papers/figures/model_comparison")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Award-winning academic science banner, FLUME AI RESEARCH typography, glowing 3D Poincare hyperbolic ball "
    "with intertwining electric cyan and gold geodesic ribbon curves, isometric transparent glass cubes, "
    "mathematical formulas, dark navy blue technical grid background, photorealistic 8k render, ultra sharp focus."
)

CANDIDATES = [
    "SDXL-Turbo",
    "Flux-2-Klein-4B",
    "Z-Image-Turbo",
    "SD-Turbo"
]

async def test_candidate(model_id: str):
    payload = {
        "model": model_id,
        "prompt": PROMPT,
        "n": 1,
        "size": "512x512",
        "response_format": "b64_json"
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            r = await client.post(LEMONADE_IMAGE_URL, json=payload)
            dt = round(time.perf_counter() - t0, 2)
            if r.status_code == 200:
                data = r.json()
                b64_str = data["data"][0].get("b64_json")
                if b64_str:
                    img_bytes = base64.b64decode(b64_str)
                    out_file = OUTPUT_DIR / f"{model_id.lower().replace('-', '_')}_sample.jpg"
                    out_file.write_bytes(img_bytes)
                    print(f"✓ `{model_id}`: SUCCESS! Generated `{out_file.name}` ({len(img_bytes)} bytes in {dt}s)")
                    return True
            else:
                print(f"• `{model_id}` notice (HTTP {r.status_code}): {r.text[:200]}")
        except Exception as e:
            print(f"• `{model_id}` error: {e}")
    return False

async def main():
    print("\n" + "=" * 115)
    print("🎨 BENCHMARKING BEST AVAILABLE LOCAL DIFFUSION MODELS (Lemonade :13305)")
    print("=" * 115)

    for cand in CANDIDATES:
        print(f"\n▶ Testing `{cand}`...")
        await test_candidate(cand)

    print("\n" + "=" * 115)
    print(f"🏆 COMPARISON SAMPLES SAVED TO: `{OUTPUT_DIR}`")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
