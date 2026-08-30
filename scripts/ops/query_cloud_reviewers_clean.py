#!/usr/bin/env python3
"""Execute Clean Multi-Perspective Cloud & Local Review."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import httpx


REVIEW_PROMPT = """You are acting as an elite Adversarial Reviewer, Experimental Plasma Physicist, and Frontier Systems Architect.
Conduct an adversarial review of Cohezion's latest breakthrough achievements:

1. **Ken Shoulders & Takaaki Matsumoto Experimental World Model**:
   - Primary 1.0 μm Toroidal EVO Core with 10^11 electrons, Bohr-Coulomb shielding, and relativistic self-pinching Bennett magnetic field (B_θ ~ 53.5 kTesla).
   - Shoulders 'String-of-Pearls' multi-vortex 5-node beaded discharges along dielectric guide channels.
   - Matsumoto paired counter-rotating helical filaments & concentric nuclear emulsion etch tracks.
   - Target cathode micro-crater borehole morphology (4.0 μm diameter × 14.2 μm depth with thermal melt ejecta lip).

2. **Zero-Error Marimo WebAssembly (WASM) Architecture**:
   - Pyodide WebAssembly micro-kernel dependency resolution using asynchronous `await micropip.install("plotly")`.
   - Strict DAG cell precedence returning explicit tuples `(mo,)` to eliminate client-side bootstrap race conditions.
   - Full Playwright automated browser verification with zero console exceptions.

3. **Multi-Silicon & Daemon Fleet Governance**:
   - Long-horizon AGI daemons (Cycles 270+) running under 20.0 GiB UMA floor and `FleetLock("modelload")`.
   - Dynamic SurrealDB System Port Registry on port 8082 with automated zero-collision allocation.

Provide your structured review in Markdown:
- **Perspective & Persona Stance**.
- **Critical Strengths & Breakthrough Capabilities**.
- **Adversarial Stress Points, Edge Cases, or Unmodelled Physical Phenomena** (e.g. dynamic charge dissipation, Bremsstrahlung radiation loss, high-order topological knotting).
- **Concrete recommendations for future sprints**.
"""

MODELS = [
    "deepseek-v4-pro:cloud",
    "qwen3.5:397b-cloud",
    "glm-5.2:cloud",
    "nemotron-3-ultra:cloud",
]


async def query_model(client: httpx.AsyncClient, model: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": REVIEW_PROMPT,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 1400},
            },
            timeout=120.0,
        )
        latency = time.perf_counter() - t0
        if resp.status_code == 200:
            data = resp.json()
            return {"model": model, "status": "success", "latency": latency, "review": data.get("response", "")}
        return {"model": model, "status": f"http_{resp.status_code}", "latency": latency, "review": resp.text}
    except Exception as e:
        return {"model": model, "status": f"error: {e}", "latency": time.perf_counter() - t0, "review": ""}


async def main() -> None:
    print("Querying 4 major frontier models...")
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[query_model(client, m) for m in MODELS])

    out_file = Path("/home/mike-anderson/dev/cohezion/docs/research/grand_multiperspective_adversarial_deep_review.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# ⚔️ Grand Multiperspective Adversarial Review: Ken Shoulders & Matsumoto World Model\n\n")
        for res in results:
            f.write(f"## 🤖 Reviewer: `{res['model']}` ({res['status']} in {res['latency']:.1f}s)\n\n")
            f.write(res['review'] + "\n\n---\n\n")
    print(f"Done! Written {out_file.stat().st_size} bytes to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
