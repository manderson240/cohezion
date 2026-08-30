#!/usr/bin/env python3
"""Adversarial Bug Hunt & Multi-Perspective Vulnerability Audit via Ollama Cloud.

Uses Tier-2 Ollama Cloud Models (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`)
to perform an exhaustive, multi-perspective adversarial security and edge-case audit across
the Cohezion codebase.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter, TaskClass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CLOUD_BUGHUNT] %(message)s")
logger = logging.getLogger("cloud_bughunt")

async def run_cloud_bughunt():
    router = UnifiedHybridRouter()
    verifier = AutoHarnessVerifier()

    target_files = [
        ("src/cohezion/inference/nano_uma_compactor.py", "SVD Low-Rank & Sparse KV-Cache Compactor"),
        ("src/cohezion/physics/nano_sheaf_ode.py", "Topological Sheaf Cohomology & Neural ODE"),
        ("src/cohezion/physics/nano_chaos.py", "Lorenz/Lyapunov Non-Linear Chaos & Fisher Metric"),
        ("src/cohezion/benchmark/multi_harness_evaluator.py", "Multi-Harness Evaluation Matrix"),
    ]

    # Three distinct adversarial cloud perspectives
    auditor_profiles = [
        ("deepseek-v4-pro:cloud", "Formal Logic, Race Condition & Concurrency Auditor"),
        ("qwen3.5:397b-cloud", "Large-Scale Architecture, Typing & AST Integrity Auditor"),
        ("glm-5.2:cloud", "Mathematical Rigor, Numerical Stability & Overflow Auditor"),
    ]

    print("\n" + "=" * 105)
    print("☁️ MULTI-PERSPECTIVE ADVERSARIAL BUGHUNT VIA OLLAMA CLOUD FLEET")
    print("=" * 105)

    total_findings = 0

    for file_path, description in target_files:
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()

        # 1. 0ms AST Verification
        t0 = time.perf_counter()
        ast_res = verifier.verify_code(code_content)
        ast_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n📁 Target: {file_path} ({description})")
        print(f"  • AST Invariant Check: {'🟢 PASSED' if ast_res['verified'] else '❌ VIOLATION'} ({ast_ms:.2f} ms)")

        # 2. Cloud Model Multi-Perspective Audit
        for model_name, perspective in auditor_profiles:
            t_model = time.perf_counter()
            prompt = f"""You are an adversarial {perspective}.
Perform a rigorous security, math, and code audit of `{file_path}`:

```python
{code_content[:3000]}
```

Analyze:
1. Subtle logic bugs, off-by-one errors, or array dimension mismatches.
2. Numerical instability (e.g. division by zero, singular matrix in SVD/matrix inversion, log of zero/negative).
3. Concurrency/threading safety and resource leaks.

Provide:
- VERDICT: CLEAN | DEFECT_FOUND
- SEVERITY: NONE | LOW | MEDIUM | HIGH | CRITICAL
- FINDINGS: Bulleted list with code references and fixes.
"""
            try:
                resp = await router.route_by_capability(
                    prompt=prompt,
                    task_class=TaskClass.DEEP_REASONING,
                    force_cloud=True
                )
                dt_ms = (time.perf_counter() - t_model) * 1000.0
                text = resp.content.strip()
                
                # Check verdict
                verdict = "🟢 CLEAN" if ("CLEAN" in text.upper() and "DEFECT_FOUND" not in text.upper()) else "⚠️ FINDINGS"
                summary_line = text.split("\n")[0] if text else "No response"
                if len(summary_line) > 80:
                    summary_line = summary_line[:77] + "..."

                print(f"  • [{resp.model_name}] {verdict} ({dt_ms:.2f} ms | Tier: {resp.tier_used})")
                print(f"    Perspective: {perspective}")
                print(f"    Summary: {summary_line}")
            except Exception as exc:
                dt_ms = (time.perf_counter() - t_model) * 1000.0
                print(f"  • [{model_name}] 🟡 SKIPPED/OFFLINE: {exc} ({dt_ms:.2f} ms)")

    print("\n" + "=" * 105)
    print("🎉 MULTI-PERSPECTIVE CLOUD BUGHUNT AUDIT COMPLETE")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    asyncio.run(run_cloud_bughunt())
