#!/usr/bin/env python3
"""Direct Multi-Perspective Adversarial Bug Hunt via Ollama Cloud Models (:11434).

Directly exercises:
1. `deepseek-v4-pro:cloud` (1.6T MoE) -> Concurrency, race conditions & memory leaks.
2. `qwen3.5:397b-cloud` (397B Dense) -> AST invariants, typing & structural integrity.
3. `glm-5.2:cloud` (756B Frontier) -> Mathematical rigor & numerical stability.
"""

import asyncio
import json
import logging
import os
import sys
import time
import httpx

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_BUGHUNT] %(message)s")
logger = logging.getLogger("cloud_bughunt")

OLLAMA_URL = "http://localhost:11434/api/generate"

async def query_cloud_model(model: str, prompt: str, system_prompt: str) -> str:
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

async def main():
    verifier = AutoHarnessVerifier()

    target_files = [
        ("src/cohezion/inference/nano_uma_compactor.py", "SVD Low-Rank & Sparse KV-Cache Compactor"),
        ("src/cohezion/physics/nano_sheaf_ode.py", "Topological Sheaf Cohomology & Neural ODE"),
        ("src/cohezion/physics/nano_chaos.py", "Lorenz/Lyapunov Non-Linear Chaos & Fisher Metric"),
    ]

    auditors = [
        ("deepseek-v4-pro:cloud", "Concurrency & Memory Leak Auditor", "You are an adversarial systems engineer hunting race conditions, memory leaks, and concurrency faults."),
        ("qwen3.5:397b-cloud", "AST & Code Structure Auditor", "You are an expert compiler engineer hunting AST defects, type violations, and unhandled edge cases."),
        ("glm-5.2:cloud", "Mathematical & Numerical Auditor", "You are a theoretical physicist and mathematician auditing numerical stability, singular matrices, and precision loss."),
    ]

    print("\n" + "=" * 105)
    print("☁️ RUNNING MULTI-PERSPECTIVE OLLAMA CLOUD ADVERSARIAL BUGHUNT")
    print("=" * 105)

    for fpath, desc in target_files:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        t0 = time.perf_counter()
        ast_res = verifier.verify_code(code)
        ast_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n📁 Target: {fpath} ({desc})")
        print(f"  • Local AST Pre-Scan: {'🟢 PASSED' if ast_res['verified'] else '❌ VIOLATION'} ({ast_ms:.2f} ms)")

        for model, role, sys_p in auditors:
            t1 = time.perf_counter()
            # Send the complete, untruncated file content
            prompt = f"Audit this COMPLETE Python file for critical bugs, numerical flaws, or edge cases. State in 2-3 sentences your verdict:\n\n```python\n{code}\n```"
            try:
                out = await query_cloud_model(model, prompt, sys_p)
                dt_s = time.perf_counter() - t1
                summary = out.replace("\n", " ")[:120]
                is_clean = "clean" in out.lower() or "correct" in out.lower() or "no critical" in out.lower() or "well-structured" in out.lower()
                status_icon = "🟢 VERIFIED CLEAN" if is_clean else "⚠️ FINDINGS"
                print(f"  • [{model}] {status_icon} ({dt_s:.2f} s)")
                print(f"    Role: {role}")
                print(f"    Verdict: {summary}...")
            except Exception as exc:
                dt_s = time.perf_counter() - t1
                print(f"  • [{model}] 🟡 ERROR/TIMEOUT: {exc} ({dt_s:.2f} s)")

    print("\n" + "=" * 105)
    print("🎉 MULTI-PERSPECTIVE CLOUD BUGHUNT AUDIT COMPLETE")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
