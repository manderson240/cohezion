#!/usr/bin/env python3
"""Execute Heterogeneous Multi-Silicon Research Plan across AMD Strix Halo (128GB UMA).

Silicon Allocation:
1. AMD XDNA2 NPU (Port 13305)  -> `deepseek-r1-0528-8b-FLM` (Sheaf Cohomology & Mathematical Invariants)
2. AMD XDNA2 NPU (Port 13305)  -> `qwen3.6-moe-35b-a3b-FLM` (Macro Action Planning & World Model Rollouts)
3. AMD Radeon 8060S iGPU       -> `Qwen3-Coder-30B` (Deterministic 128k Code AST Verifier Synthesis)
4. AMD Radeon 8060S iGPU       -> `gpt-oss-20b` (Adversarial Red-Team & Edge Case Identification)
5. AMD Ryzen 9 CPU + Threads   -> 16-Core High-Throughput CFR Game Rollouts & Graph Verification
"""

import asyncio
import json
import logging
import os
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SILICON_RESEARCH] %(message)s")
logger = logging.getLogger("silicon_research")

LEMONADE_BASE = "http://localhost:13305"

RESEARCH_PROMPTS = [
    {
        "lane": "AMD XDNA2 NPU (MoE - Pinned 262k)",
        "model": "qwen3.6-moe-35b-a3b-FLM",
        "role": "Macro Action Planner & World Model",
        "objective": "Formulate high-level Macro DSL sequence tokens for multi-room flood fill and collision raycasting.",
        "prompt": "You are an Action Planner on AMD XDNA2 NPU. Define a 5-step tokenized macro DSL plan ([ROOM_DETECT, RAYCAST_BOUNCE, PAIR_CONNECT]) to solve complex geometric grid tasks in microsecond execution."
    },
    {
        "lane": "AMD Radeon 8060S iGPU (128K MXFP4)",
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "role": "Adversarial Red-Team Auditor & Invariant Hunter",
        "objective": "Perform an adversarial stress audit identifying edge-case failures in the proposed Sheaf & Macro DSL solvers.",
        "prompt": "You are a Cynical Red-Team Auditor on Radeon 8060S iGPU. Attack the Sheaf Cohomology and Macro DSL approach. Identify 3 catastrophic edge cases (e.g. disconnected components, periodic boundary wrap, non-Euclidean lattices) where this method fails, and propose concrete algorithmic patches."
    },
    {
        "lane": "AMD Radeon 8060S iGPU (ROCm LLM)",
        "model": "Qwen3-8B-GGUF",
        "role": "AST Code Synthesizer",
        "objective": "Generate high-performance Python AST action-verifier code for AutoHarness (arXiv:2603.03329v1).",
        "prompt": "You are a Principal Software Engineer. Write a complete, standalone Python function `verify_grid_invariants(input_grid, output_grid)` enforcing color conservation, bounding box consistency, and topological connectivity in <0.01ms."
    },
    {
        "lane": "AMD Ryzen 9 CPU / NPU (Fast Edge)",
        "model": "waslmedia-qwen3-4b-Q4_K_M",
        "role": "Formal Proof Lemma Validator",
        "objective": "Verify mathematical lemma steps for Čech cohomology vanishing delta^0(s)_{ij} = 0.",
        "prompt": "You are a Mathematical Validator. Verify the discrete boundary condition delta^0(s)_{ij} = 0 for 2D cell grid intersection gluing."
    }
]

async def query_silicon_lane(client: httpx.AsyncClient, item: dict) -> dict:
    logger.info("Dispatching to %s (%s) - %s...", item["lane"], item["model"], item["role"])
    t0 = time.perf_counter()
    payload = {
        "model": item["model"],
        "messages": [
            {"role": "system", "content": f"You are acting as an elite {item['role']} on AMD Strix Halo Silicon."},
            {"role": "user", "content": item["prompt"]}
        ],
        "temperature": 0.2,
        "max_tokens": 4096
    }
    try:
        r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return {
                "lane": item["lane"],
                "model": item["model"],
                "role": item["role"],
                "duration_seconds": dt,
                "status": "SUCCESS",
                "output": content.strip()
            }
        else:
            return {"lane": item["lane"], "model": item["model"], "status": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"lane": item["lane"], "model": item["model"], "status": f"Exception: {e}"}

async def main():
    print("\n" + "=" * 115)
    print("🚀 EXECUTING MULTI-SILICON HETEROGENEOUS RESEARCH PLAN (AMD STRIX HALO)")
    print("=" * 115)

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Run all silicon research lanes concurrently across NPU, iGPU, and CPU
        tasks = [query_silicon_lane(client, item) for item in RESEARCH_PROMPTS]
        results = await asyncio.gather(*tasks)

    os.makedirs("docs/research", exist_ok=True)
    report_file = "docs/research/multi_silicon_research_plan_execution.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 🚀 Multi-Silicon Sovereign Research Plan & Execution Report\n\n")
        f.write("**Hardware**: AMD Strix Halo (128GB Unified Memory, XDNA2 NPU, Radeon 8060S iGPU, Ryzen 9 CPU)  \n")
        f.write("**Date**: 2026-08-24  \n\n")
        f.write("## 1. Executive Summary\n\n")
        f.write("A 4-way heterogeneous silicon execution plan was run natively on local hardware across distinct cognitive roles.\n\n")

        for res in results:
            print(f"\n[{res['lane']}: {res['model']}] ({res.get('role', 'Agent')})")
            print(f"  ├─ Status   : {res['status']}")
            print(f"  ├─ Duration : {res.get('duration_seconds', 0)}s")
            print(f"  └─ Output   : {res.get('output', '')[:200]}...\n")

            f.write(f"### {res['lane']} — `{res['model']}` ({res.get('role', 'Agent')})\n\n")
            f.write(f"- **Execution Time**: {res.get('duration_seconds', 0)}s  \n")
            f.write(f"- **Status**: {res['status']}  \n\n")
            f.write(f"```markdown\n{res.get('output', '')}\n```\n\n---\n\n")

    print("=" * 115)
    print(f"📄 Multi-Silicon Research Plan persisted to: {report_file}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
