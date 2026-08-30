#!/usr/bin/env python3
"""Validation & Verification (V&V) of Cohezion Architecture via Ollama Cloud Streaming API."""

import asyncio
import json
import os
import time
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"

AUDIT_PROMPT = """Conduct an independent Verification and Validation (V&V) audit of the Cohezion sovereign architecture on AMD Strix Halo silicon (128GB unified memory):

1. Poincaré 2048D Hyperbolic Space with Penrose conformal boundary regularization W(x) = sqrt(1 - ||x||^2) * x.
2. CTAC Topological Allostasis maintaining the HIHO 0.50 coherence attractor (maximum entropy, maximum microstates).
3. AMD Quark OCP MXFP4 Quantization (+20.27 dB SNR, 8x compression) & ZenTorch AVX-512 Fréchet mean solver (0.898 ms).
4. SurrealDB bi-temporal graph & HNSW vector storage with 0ms cloud egress.

In 3 concise sections:
- Formal Verification: Is the physics and mathematical formulation sound?
- Systems Validation: Does the multi-silicon pipeline prevent memory/compute bottlenecks?
- Verdict: PASS / CONDITIONAL / FAIL (Score: 0.00 - 1.00)."""

CLOUD_MODELS = [
    ("deepseek-v4-flash:cloud", "Tier-2 Fast Frontier Reasoning Model"),
    ("gpt-oss:120b-cloud", "Tier-2 Frontier 120B Systems Verifier")
]

async def query_cloud_stream(model_id: str, desc: str):
    print(f"\n▶ Querying Cloud Model: `{model_id}` ({desc})...")
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "You are a Principal Systems and Formal Verification Engineer."},
            {"role": "user", "content": AUDIT_PROMPT}
        ],
        "stream": True,
        "options": {"temperature": 0.2}
    }
    
    t0 = time.perf_counter()
    full_text = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            if response.status_code != 200:
                print(f"  ✗ Cloud API error: HTTP {response.status_code}")
                return None, 0.0
            
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    msg = data.get("message", {})
                    token = msg.get("content", "")
                    if token:
                        full_text.append(token)
                        
    dt = round(time.perf_counter() - t0, 2)
    joined_text = "".join(full_text).strip()
    if "</think>" in joined_text:
        joined_text = joined_text.split("</think>")[-1].strip()
    
    print(f"  ✓ {model_id} Completed in {dt}s ({len(joined_text)} chars):\n")
    print(joined_text[:450] + "...\n")
    return joined_text, dt

async def main():
    print("\n" + "=" * 115)
    print("☁️ OLLAMA CLOUD INDEPENDENT VERIFICATION & VALIDATION (V&V) STREAMING SUITE")
    print("=" * 115)

    reports = []
    for model_id, desc in CLOUD_MODELS:
        text, dt = await query_cloud_stream(model_id, desc)
        if text:
            reports.append((model_id, text, dt))

    os.makedirs("docs/research", exist_ok=True)
    report_path = "docs/research/ollama_cloud_vv_audit_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ☁️ Ollama Cloud Independent Verification & Validation (V&V) Report\n\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  \n")
        f.write("**Evaluated System**: Cohezion Sovereign Strix Halo Stack (AMD XDNA2 + RDNA 3.5 + Zen 9 + SurrealDB)  \n\n")
        f.write("---\n\n")
        for model_id, text, dt in reports:
            f.write(f"## ✦ Independent Audit: `{model_id}` (Response Time: {dt}s)\n\n")
            f.write(f"{text}\n\n---\n\n")

    print("=" * 115)
    print(f"📄 V&V Report Persisted to: {report_path}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
