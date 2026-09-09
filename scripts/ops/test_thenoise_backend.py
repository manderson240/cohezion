#!/usr/bin/env python3
"""Testing the Local `thenoise` C++ Diffusion Engine via Lemonade Server (:13305).

Models on `thenoise` backend:
1. `Z-Image-Turbo-TheNoise` (1024x1024 / 8 steps / cfg 1.0)
2. `Krea-2-Turbo` (1024x1024 / 8 steps / cfg 1.0)
3. `Anima-Turbo` (1024x1024 / 8 steps / cfg 1.0)
"""

import asyncio
import base64
import httpx
import time
from pathlib import Path

LEMONADE_IMAGE_URL = "http://localhost:13305/v1/images/generations"
OUTPUT_DIR = Path("docs/papers/figures/thenoise_hd")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Award-winning academic science banner, FLUME AI RESEARCH header in crisp modern sans-serif typography, "
    "central glowing 3D spherical Poincare wireframe with intertwining electric cyan and gold geodesic ribbon curves, "
    "isometric translucent glass cubes, mathematical formulas, dark navy blue technical blueprint grid background, sharp focus, 8k render."
)

THENOISE_MODELS = [
    "Z-Image-Turbo-TheNoise",
    "Krea-2-Turbo",
    "Anima-Turbo"
]

async def test_thenoise_model(model_id: str):
    print(f"\n▶ Testing `thenoise` Engine Model: `{model_id}`...")
    payload = {
        "model": model_id,
        "prompt": PROMPT,
        "n": 1,
        "size": "1024x1024",
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
                    out_file = OUTPUT_DIR / f"{model_id.lower().replace('-', '_')}.jpg"
                    out_file.write_bytes(img_bytes)
                    print(f"   ✓ `{model_id}` on `thenoise`: SUCCESS! Generated `{out_file.name}` ({len(img_bytes)} bytes in {dt}s)")
                    return True
            else:
                print(f"   • `{model_id}` notice (HTTP {r.status_code}): {r.text[:200]}")
        except Exception as e:
            print(f"   • `{model_id}` error: {e}")
    return False

async def main():
    print("\n" + "=" * 115)
    print("🚀 TESTING LEMONADE `thenoise` HIGH-PERFORMANCE C++ DIFFUSION BACKEND")
    print("=" * 115)

    for m in THENOISE_MODELS:
        await test_thenoise_model(m)

    print("\n" + "=" * 115)
    print(f"🏆 THENOISE BENCHMARK COMPLETE! Outputs saved in `{OUTPUT_DIR}`")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
