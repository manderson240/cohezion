#!/usr/bin/env python3
"""Grand Dual-Fleet Multi-Perspective Adversarial Review.

Dispatches structured adversarial reviews across:
1. **Tier-1 Local Silicon (Lemonade :13305)**:
   - `gpt-oss-20b-mxfp4-GGUF` (iGPU Resident) -> Memory safety, UMA allocation, and AST invariants.
2. **Tier-2 Ollama Cloud Fleet (:11434)**:
   - `deepseek-v4-pro:cloud` (1.6T MoE) -> Concurrency, race conditions & distributed graph invariants.
   - `qwen3.5:397b-cloud` (397B Dense) -> Architectural scaling, API boundaries & typing.
   - `glm-5.2:cloud` (756B Frontier) -> Mathematical rigor & topological stability.
"""

import asyncio
import json
import logging
import os
import sys
import time
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [DUAL_REVIEW] %(message)s")
logger = logging.getLogger("dual_review")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

AUDIT_TARGETS = [
    ("src/cohezion/compound/goals_and_loops_orchestrator.py", "Goals & Staged Loops Autonomous Delivery Engine"),
    ("src/cohezion/graph/graph_engine.py", "SurrealDB v2 Knowledge Graph Mesh & Relational Topology"),
    ("src/cohezion/inference/nano_uma_compactor.py", "SVD Low-Rank + Sparse UMA KV-Cache Compactor"),
    ("src/cohezion/physics/nano_chaos.py", "Nonlinear Dynamics & Benettin Lyapunov Renormalization"),
]

REVIEWERS = [
    # Tier-1 Local Silicon
    {
        "name": "gpt-oss-20b (Lemonade iGPU)",
        "tier": "Tier 1 (Local Silicon)",
        "backend": "lemonade",
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "stance": "Cynical Kernel & Local Memory Architect",
        "system": "You are a cynical hardware/kernel architect auditing code for UMA memory overhead, cache efficiency, and buffer overflow risks."
    },
    # Tier-2 Ollama Cloud
    {
        "name": "deepseek-v4-pro:cloud (1.6T MoE)",
        "tier": "Tier 2 (Ollama Cloud)",
        "backend": "ollama",
        "model": "deepseek-v4-pro:cloud",
        "stance": "Distributed Systems & Concurrency Auditor",
        "system": "You are a distributed systems engineer hunting race conditions, deadlock vectors, and graph cycle hazards."
    },
    {
        "name": "qwen3.5:397b-cloud (397B Dense)",
        "tier": "Tier 2 (Ollama Cloud)",
        "backend": "ollama",
        "model": "qwen3.5:397b-cloud",
        "stance": "Principal Software & Type System Architect",
        "system": "You are a Principal Software Architect enforcing Python 3.13 typing standards, clean API abstractions, and maintainability."
    },
    {
        "name": "glm-5.2:cloud (756B Frontier)",
        "tier": "Tier 2 (Ollama Cloud)",
        "backend": "ollama",
        "model": "glm-5.2:cloud",
        "stance": "Theoretical Physicist & Mathematical Rigor Lead",
        "system": "You are a theoretical physicist evaluating mathematical validity, topological stability, and numerical convergence proofs."
    }
]

async def query_lemonade(model: str, prompt: str, system_prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post(LEMONADE_URL, json=payload)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        return f"HTTP Error {r.status_code}: {r.text}"

async def query_ollama(model: str, prompt: str, system_prompt: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9}
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(OLLAMA_URL, json=payload)
        if r.status_code == 200:
            data = r.json()
            raw = (data.get("response") or data.get("thinking") or "").strip()
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            return raw
        return f"HTTP Error {r.status_code}"

async def run_dual_fleet_review():
    print("\n" + "=" * 105)
    print("⚔️ GRAND DUAL-FLEET MULTI-PERSPECTIVE ADVERSARIAL REVIEW (Lemonade :13305 + Ollama :11434)")
    print("=" * 105)

    review_report = {}

    for fpath, desc in AUDIT_TARGETS:
        if not os.path.exists(fpath):
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        print(f"\n📂 Target: {fpath} ({desc})")
        review_report[fpath] = []

        for rev in REVIEWERS:
            t0 = time.perf_counter()
            prompt = f"Adversarially review this Python module from your perspective. State (1) Verdict [CLEAN/DEFECT], (2) Critical Risk Score (0-10), and (3) Key Strengths / Vulnerabilities in 2-3 concise sentences:\n\n```python\n{code[:2500]}\n```"
            
            try:
                if rev["backend"] == "lemonade":
                    res = await query_lemonade(rev["model"], prompt, rev["system"])
                else:
                    res = await query_ollama(rev["model"], prompt, rev["system"])

                dt_s = time.perf_counter() - t0
                summary = res.replace("\n", " ")[:110]
                is_clean = "clean" in res.lower() or "verdict: clean" in res.lower() or "risk: 0" in res.lower() or "risk: 1" in res.lower()
                status_icon = "🟢 VERIFIED" if is_clean else "⚠️ ADVISORY"

                print(f"  • [{rev['name']}] {status_icon} ({dt_s:.2f}s | {rev['tier']})")
                print(f"    Stance : {rev['stance']}")
                print(f"    Review : {summary}...")

                review_report[fpath].append({
                    "reviewer": rev["name"],
                    "stance": rev["stance"],
                    "verdict": "CLEAN" if is_clean else "FINDINGS",
                    "latency_sec": round(dt_s, 2),
                    "notes": res
                })
            except Exception as exc:
                dt_s = time.perf_counter() - t0
                print(f"  • [{rev['name']}] 🟡 OFFLINE/SKIPPED: {exc} ({dt_s:.2f}s)")

    print("\n" + "=" * 105)
    print("🎉 DUAL-FLEET MULTI-PERSPECTIVE ADVERSARIAL REVIEW COMPLETE")
    print("=" * 105 + "\n")

    # Persist report
    out_path = "docs/research/dual_fleet_multiperspective_review.json"
    os.makedirs("docs/research", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(review_report, f, indent=2)
    logger.info("Saved review matrix to %s", out_path)

if __name__ == "__main__":
    asyncio.run(run_dual_fleet_review())
