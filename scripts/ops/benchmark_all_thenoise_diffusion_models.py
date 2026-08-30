#!/usr/bin/env python3
"""Auditing and Benchmarking All Candidate Diffusion Models on Lemonade / `thenoise` Engine.

Candidates:
1. `Z-Image-Turbo-TheNoise` (1024x1024 / Native ROCm 7.14 C++ thenoise diffusion backend, 20.7 GB)
2. `Krea-2-Turbo` (1024x1024 / 8 steps / cfg 1.0)
3. `Anima-Turbo` (1024x1024 / 8 steps / cfg 1.0)
4. `SDXL-Turbo` (512x512 to 1024x1024 / single step / fast)
5. `FLUX.1-schnell` / `FLUX.2-Turbo` (Frontier 12B flow-matching transformer diffusion)
"""

import asyncio
import base64
import time
import httpx
from pathlib import Path

LEMONADE_IMAGE_URL = "http://localhost:13305/v1/images/generations"
OUT_DIR = Path("docs/papers/figures/diffusion_model_shootout")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Award-winning scientific illustration of a 12-dimensional Poincare hyperbolic manifold, "
    "glowing electric cyan and amber geodesic ribbon curves traversing the unit sphere, "
    "translucent glass volumetric depth, crystalline geometric facets, deep obsidian navy background, "
    "clean mathematical vector precision, raytraced caustic lighting, 8k resolution."
)

CANDIDATES = [
    ("Z-Image-Turbo-TheNoise", "1024x1024"),
    ("Krea-2-Turbo", "1024x1024"),
    ("Anima-Turbo", "1024x1024"),
    ("SDXL-Turbo", "512x512"),
    ("SDXL-Turbo", "1024x1024"),
    ("FLUX.1-schnell", "1024x1024"),
]

async def benchmark_candidate(name: str, res: str):
    print(f"\n▶ Testing Model: `{name}` @ {res}...")
    payload = {
        "model": name,
        "prompt": PROMPT,
        "n": 1,
        "size": res,
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
                    fname = f"{name.lower().replace('.', '_').replace('-', '_')}_{res}.jpg"
                    out_file = OUT_DIR / fname
                    out_file.write_bytes(img_bytes)
                    print(f"   ✓ SUCCESS! Rendered `{fname}` ({len(img_bytes)} bytes in {dt}s)")
                    return True, dt, len(img_bytes)
            else:
                print(f"   • Notice ({r.status_code}): {r.text[:120]}")
        except Exception as e:
            print(f"   • Exception: {e}")
    return False, 0.0, 0

async def main():
    print("=" * 105)
    print("🔬 DIFFUSION BENCHMARK SHOOTOUT: AUDITING ALL AVAILABLE `thenoise` & DIFFUSION MODELS")
    print("=" * 105)

    results = []
    for name, res in CANDIDATES:
        ok, dt, size_b = await benchmark_candidate(name, res)
        results.append((name, res, ok, dt, size_b))
        await asyncio.sleep(1.0)

    print("\n" + "=" * 105)
    print("📊 BENCHMARK SHOOTOUT RESULTS:")
    print("=" * 105)
    for name, res, ok, dt, size_b in results:
        status_str = f"ACTIVE ({dt}s, {size_b/1024:.1f} KB)" if ok else "INACTIVE / NOT_DOWNLOADED"
        print(f"• `{name:24}` [{res:9}] -> {status_str}")

if __name__ == "__main__":
    asyncio.run(main())
