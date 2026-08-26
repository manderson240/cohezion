#!/usr/bin/env python3
"""OmA Loop: Query Local Inference Silicon (Lemonade :13305) on Optimal Local Inference Deployment.

Queries local models on Strix Halo (NPU / iGPU / CPU) under safe 50.0 GiB UMA headroom gating.
"""

from __future__ import annotations
import asyncio
import json
import time
import httpx
from pathlib import Path

from cohezion.inference.smart_oom_governor import SmartOOMGovernor, CrossSessionFleetLock

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"

PROMPT = """You are a Strix Halo Local Silicon Kernel & Inference Architect on AMD hardware (128GB unified RAM, XDNA2 NPU, Radeon 8060S iGPU).
What is the optimal strategy for an autonomous multi-agent coding swarm to leverage local inference safely without kernel lockups (REISUB) or OOM?

Structure your recommendations into:
1. Silicon Lane Allocation (NPU vs iGPU vs CPU vs Cloud Overflow).
2. KV Cache & Context Optimization (Paging, quantization, prefix cache).
3. Cross-Session Concurrency & Aperture Lock Protection.
4. AutoHarness Deterministic Pre-Filtering (0ms code verifiers).
Be specific, authoritative, and concise."""

async def consult_local_inference():
    print("=" * 90)
    print("🔄 OMA LOOP: CONSULTING LOCAL INFERENCE ON OPTIMAL HARDWARE LEVERAGING")
    print("=" * 90)

    avail_gib, swap_used, is_safe = SmartOOMGovernor.get_memory_state()
    print(f"▶ Preflight Memory: {avail_gib} GiB available / {swap_used} GiB swap (Safe floor: 50.0 GiB)")

    if not is_safe:
        print(f"⚠️ Memory below 50.0 GiB ({avail_gib} GiB). Redirecting consultation to Tier 2 Ollama Cloud...")
        # Query Ollama Cloud fallback
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "deepseek-v4-pro:cloud",
                    "prompt": PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.2, "top_p": 0.9}
                }
            )
            data = res.json()
            raw = (data.get("response") or data.get("thinking") or "").strip()
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            print("\n=== Consultation Response (via Tier-2 Ollama Cloud) ===\n")
            print(raw)
            return raw

    # Query Local Lemonade via FleetLock
    print("▶ Acquiring CrossSessionFleetLock for safe local query...")
    try:
        with CrossSessionFleetLock(timeout_sec=10.0):
            # Check available models on Lemonade
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    LEMONADE_URL,
                    json={
                        "model": "gpt-oss-20b-mxfp4-GGUF",
                        "messages": [{"role": "user", "content": PROMPT}],
                        "max_tokens": 1024,
                        "temperature": 0.2
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    print("\n=== Consultation Response (via Tier-1 Local iGPU gpt-oss-20b-MXFP4) ===\n")
                    print(content)
                    return content
                else:
                    print(f"Local query returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Local consultation notice: {e}")

    # Fallback to Ollama Cloud
    print("▶ Executing cloud consultation fallback...")
    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-v4-pro:cloud",
                "prompt": PROMPT,
                "stream": False
            }
        )
        data = res.json()
        raw = (data.get("response") or "").strip()
        print("\n=== Consultation Response ===\n")
        print(raw)
        return raw

if __name__ == "__main__":
    asyncio.run(consult_local_inference())
