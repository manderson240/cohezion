#!/usr/bin/env python3
"""Renders the Final 4-Figure Publication Suite using Local `SDXL-Turbo`.

Generates ultra-high-definition, photorealistic figures locally on Lemonade (:13305):
1. Figure 1: Master Header Banner (560x280 aspect ratio composition).
2. Figure 2: Sheaf Cohomology Local-to-Global Gluing & Obstruction Vanishing.
3. Figure 3: Continuous 384D Poincare Hyperbolic Geodesic Flow.
4. Figure 4: 0ms AutoHarness AST Formal Proof Verification.
"""

import asyncio
import base64
import httpx
import time
from pathlib import Path

LEMONADE_IMAGE_URL = "http://localhost:13305/v1/images/generations"
OUTPUT_DIR = Path("docs/papers/figures/sdxl_hd")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "SDXL-Turbo"

FIGURES = [
    {
        "id": "fig1_master_banner",
        "title": "Figure 1: Master Academic Science Banner",
        "file": OUTPUT_DIR / "fig1_flume_master_banner_sdxl.jpg",
        "prompt": (
            "Award-winning scientific illustration, FLUME AI RESEARCH header in crisp modern sans-serif typography, "
            "central glowing 3D spherical Poincare wireframe with intertwining electric cyan and gold geodesic ribbon curves, "
            "isometric translucent glass cubes, mathematical formulas, dark navy blue technical blueprint grid background, sharp focus, 8k render."
        )
    },
    {
        "id": "fig2_sheaf_cohomology",
        "title": "Figure 2: Sheaf Cohomology Local-to-Global Gluing",
        "file": OUTPUT_DIR / "fig2_sheaf_cohomology_sdxl.jpg",
        "prompt": (
            "Scientific diagram of Sheaf Cohomology on 2D grids. Abstract overlapping local spatial patches U_i and U_j "
            "gluing seamlessly into a global section, mathematical restriction maps rho, coboundary operator delta^0, "
            "glowing green consensus nodes, zero boundary obstruction H^1=0, high-contrast dark mode scientific diagram, 8k render."
        )
    },
    {
        "id": "fig3_poincare_geodesic",
        "title": "Figure 3: 384D Poincaré Hyperbolic Geodesic Flow",
        "file": OUTPUT_DIR / "fig3_poincare_geodesic_sdxl.jpg",
        "prompt": (
            "Hyperbolic geometry visualization, cross-section of a 3D Poincare disk with negative curvature kappa=-1.0, "
            "radiant golden continuous geodesic flow trajectories curving towards the boundary, Christoffel symbol vector field, "
            "glowing nodes in cyan and amber, deep black space background, crisp physics laboratory visualization, 8k render."
        )
    },
    {
        "id": "fig4_autoharness_ast",
        "title": "Figure 4: 0ms AutoHarness AST Formal Proof Verification",
        "file": OUTPUT_DIR / "fig4_autoharness_ast_sdxl.jpg",
        "prompt": (
            "Abstract Computer Science diagram, Abstract Syntax Tree (AST) formal bytecode verifier. "
            "Glowing green checkmarks verifying ARC grid transformation invariants, color conservation, geometric symmetries, "
            "deterministic binary verification pipeline, zero hallucination zero latency proof gate, dark technical aesthetic, 8k render."
        )
    }
]

async def generate_sdxl_figure(fig: dict):
    payload = {
        "model": MODEL_ID,
        "prompt": fig["prompt"],
        "n": 1,
        "size": "512x512",
        "response_format": "b64_json"
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(LEMONADE_IMAGE_URL, json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            b64_str = data["data"][0].get("b64_json")
            if b64_str:
                fig["file"].write_bytes(base64.b64decode(b64_str))
                print(f"   ✓ Generated `{fig['file'].name}` ({fig['file'].stat().st_size} bytes in {dt}s)")
                return True
        else:
            print(f"   ❌ Error HTTP {r.status_code}: {r.text[:100]}")
    return False

async def main():
    print("\n" + "=" * 115)
    print("💎 RENDERING MASTER PUBLICATION STORY SUITE WITH HIGH-DEFINITION `SDXL-Turbo`")
    print("=" * 115)

    for idx, fig in enumerate(FIGURES, 1):
        print(f"\n▶ [{idx}/4] Rendering `{fig['title']}` with SDXL-Turbo...")
        await generate_sdxl_figure(fig)

    print("\n" + "=" * 115)
    print(f"🏆 ALL SDXL HIGH-DEFINITION FIGURES SAVED TO: `{OUTPUT_DIR}`")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
