#!/usr/bin/env python3
"""Local Multi-Perspective Adversarial Pre-Flight Audit.

Executes a 4-Persona Adversarial Review running entirely on Local Silicon (:13305):
- Persona 1: Cynical Systems & In-Container Runtime Architect (`Qwen3-Coder-30B` on iGPU)
- Persona 2: Formal Verification & Invariant Proof Auditor (`gpt-oss-20b-mxfp4` on iGPU)
- Persona 3: Competitive ML Grandmaster & Leaderboard Strategist (`qwen3.6-moe-35b-a3b` on NPU)
- Persona 4: Sovereign Hardware & OOM Governor (`waslmedia-qwen3-4b` on NPU)

Evaluates:
1. 384D Poincaré Geodesic search integration.
2. The 5 synthesized ARC DSL primitives (gravity, convex hull, compactness, anti-diagonal, periodic tile).
3. 9-hour container runtime safety, memory ceiling, and submission slot economics.
"""

import asyncio
import httpx
import json
import time
from pathlib import Path
from cohezion.core.typed_context import TypedContextStore, ContextType

LEMONADE_CHAT_URL = "http://localhost:13305/v1/chat/completions"
REPORT_PATH = Path("docs/research/local_multiperspective_preflight_audit.md")

AUDIT_SCOPE = """
We are preparing Day 1 Anchor Submissions for ARC-AGI-2 and ARC-AGI-3 on Kaggle:
- Upgrade from 2048D to 384D Poincare Hyperbolic Manifold (10.91x faster, 227k evals/sec).
- 5 Synthesized DSL primitives (Gravity drop, Convex hull envelope fill, Perimeter-to-area compactness remap, Anti-diagonal reflection, Periodic tile extrapolation).
- 0ms AutoHarness AST proof verification ensuring zero training exemplar errors.
- 9-Hour in-container execution window on Dual NVIDIA T4 GPUs / CPU fallback.
- Quota: 4 slots left on ARC-2, 5 slots left on ARC-3 today.
"""

PERSONAS = [
    {
        "id": "cynical_runtime",
        "name": "Cynical In-Container Runtime Architect",
        "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "sys": "You are a brutally cynical Kaggle container runtime architect. Attack edge cases, execution timeouts, memory leaks, and dependency failures in ARC kernels."
    },
    {
        "id": "formal_verifier",
        "name": "Formal Verification & Invariant Auditor",
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "sys": "You are a Formal Verification Lead. Audit AutoHarness AST verification proofs, mathematical bounds, and false positive risks."
    },
    {
        "id": "ml_grandmaster",
        "name": "Competitive ML Grandmaster",
        "model": "qwen3.6-moe-35b-a3b-FLM",
        "sys": "You are a Kaggle Grandmaster. Evaluate leaderboard score upside, test-time compute search depth, and submission slot strategy."
    },
    {
        "id": "hardware_governor",
        "name": "Sovereign Hardware & Memory Governor",
        "model": "waslmedia-qwen3-4b-Q4_K_M",
        "sys": "You are a Hardware Safety Governor. Evaluate UMA memory footprint, NPU/iGPU execution stability, and thermal limits."
    }
]

async def query_persona(persona: dict) -> tuple[str, str, float]:
    prompt = f"{AUDIT_SCOPE}\n\nDeliver your rigorous adversarial audit from your persona's perspective. Highlight critical vulnerabilities, failure modes, and your final GO / NO-GO verdict."
    payload = {
        "model": persona["model"],
        "messages": [
            {"role": "system", "content": persona["sys"]},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 600
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            r = await client.post(LEMONADE_CHAT_URL, json=payload)
            dt = round(time.perf_counter() - t0, 2)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content", "").strip()
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                return persona["name"], content, dt
        except Exception as e:
            return persona["name"], f"Local model execution note: {e}", -1.0
    return persona["name"], "No response", -1.0

async def run_local_multiperspective_audit():
    print("\n" + "=" * 115)
    print("🛡️ LAUNCHING 4-PERSONA LOCAL ADVERSARIAL PRE-FLIGHT AUDIT (:13305)")
    print("=" * 115)

    store = TypedContextStore()
    report_sections = [
        "# Local Multi-Perspective Adversarial Pre-Flight Audit Report",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "**Infrastructure:** Lemonade OmniRouter (:13305) on AMD Strix Halo Local Silicon",
        "**Scope:** ARC Prize 2 & 3 Anchor Submissions (384D Poincaré + 5 Synthesized Primitives)",
        "\n---\n"
    ]

    for persona in PERSONAS:
        print(f"\n▶ Auditing with `{persona['name']}` ({persona['model']})...")
        name, review, dt = await query_persona(persona)
        print(f"   ✓ {name} completed in {dt}s")
        
        report_sections.append(f"## Persona: {name} (`{persona['model']}`)\n")
        report_sections.append(f"**Latency:** {dt}s\n")
        report_sections.append(f"{review}\n\n---\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report_sections))
    print("\n" + "=" * 115)
    print(f"🏆 ALL 4 LOCAL PERSONA AUDITS COMPLETE! Saved to `{REPORT_PATH}`")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_local_multiperspective_audit())
