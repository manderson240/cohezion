#!/usr/bin/env python3
"""Sequential Multi-Silicon Research Plan across Lemonade Models.

Executes sequential queries to respect Lemonade FleetLock and prevent concurrent model load aperture collisions.
"""

import asyncio
import json
import logging
import os
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SEQUENTIAL_RESEARCH] %(message)s")
logger = logging.getLogger("sequential_research")

LEMONADE_BASE = "http://localhost:13305"

RESEARCH_ROSTER = [
    {
        "silicon_lane": "AMD XDNA2 NPU (MoE - 262k Pinned)",
        "model": "qwen3.6-moe-35b-a3b-FLM",
        "role": "Macro Action Planner & World Model",
        "prompt": "You are an Action Planner on AMD XDNA2 NPU. Define a 5-step tokenized macro DSL plan ([ROOM_DETECT, RAYCAST_BOUNCE, PAIR_CONNECT]) to solve complex geometric grid tasks in microsecond execution."
    },
    {
        "silicon_lane": "AMD Radeon 8060S iGPU (128K MXFP4)",
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "role": "Adversarial Red-Team Auditor & Invariant Hunter",
        "prompt": "You are a Cynical Red-Team Auditor on Radeon 8060S iGPU. Attack the Sheaf Cohomology and Macro DSL approach. Identify 3 catastrophic edge cases (e.g. disconnected components, periodic boundary wrap, non-Euclidean lattices) where this method fails, and propose concrete algorithmic patches."
    },
    {
        "silicon_lane": "AMD Radeon 8060S iGPU (ROCm LLM)",
        "model": "Qwen3-8B-GGUF",
        "role": "AST Code Synthesizer",
        "prompt": "You are a Principal Software Engineer. Write a complete, standalone Python function `verify_grid_invariants(input_grid, output_grid)` enforcing color conservation, bounding box consistency, and topological connectivity in <0.01ms."
    },
    {
        "silicon_lane": "AMD Ryzen 9 CPU / NPU (Fast Edge)",
        "model": "waslmedia-qwen3-4b-Q4_K_M",
        "role": "Formal Proof Lemma Validator",
        "prompt": "You are a Mathematical Validator. Verify the discrete boundary condition delta^0(s)_{ij} = 0 for 2D cell grid intersection gluing."
    }
]

async def main():
    print("\n" + "=" * 115)
    print("🚀 SEQUENTIAL MULTI-SILICON RESEARCH EXECUTION (FLEETLOCK SAFE)")
    print("=" * 115)

    results = []
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        for item in RESEARCH_ROSTER:
            print(f"\n▶ Executing Silicon Lane: {item['silicon_lane']} ({item['model']})...")
            t0 = time.perf_counter()
            payload = {
                "model": item["model"],
                "messages": [
                    {"role": "system", "content": f"You are acting as an elite {item['role']} on AMD Strix Halo Silicon."},
                    {"role": "user", "content": item["prompt"]}
                ],
                "temperature": 0.2,
                "max_tokens": 2048
            }
            try:
                r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload)
                dt = round(time.perf_counter() - t0, 2)
                if r.status_code == 200:
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    content = msg.get("content") or msg.get("reasoning_content") or ""
                    print(f"  ✓ Success in {dt}s ({len(content)} chars)")
                    results.append({
                        "lane": item["silicon_lane"],
                        "model": item["model"],
                        "role": item["role"],
                        "duration_seconds": dt,
                        "status": "SUCCESS",
                        "output": content.strip()
                    })
                else:
                    print(f"  ✗ HTTP {r.status_code}: {r.text[:100]}")
                    results.append({"lane": item["silicon_lane"], "model": item["model"], "status": f"HTTP {r.status_code}"})
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                results.append({"lane": item["silicon_lane"], "model": item["model"], "status": f"Exception: {e}"})

    os.makedirs("docs/research", exist_ok=True)
    report_file = "docs/research/multi_silicon_research_plan_execution.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 🚀 Multi-Silicon Sovereign Research Plan & Execution Report\n\n")
        f.write("**Hardware**: AMD Strix Halo (128GB Unified Memory, XDNA2 NPU, Radeon 8060S iGPU, Ryzen 9 CPU)  \n")
        f.write("**Date**: 2026-08-24  \n\n")
        f.write("## 1. Executive Summary\n\n")
        f.write("A 4-way heterogeneous silicon execution plan was run natively on local hardware across distinct cognitive roles.\n\n")

        for res in results:
            f.write(f"### {res['lane']} — `{res['model']}` ({res.get('role', 'Agent')})\n\n")
            f.write(f"- **Execution Time**: {res.get('duration_seconds', 0)}s  \n")
            f.write(f"- **Status**: {res['status']}  \n\n")
            f.write(f"```markdown\n{res.get('output', '')}\n```\n\n---\n\n")

    print("\n" + "=" * 115)
    print(f"📄 Multi-Silicon Research Plan saved to: {report_file}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
