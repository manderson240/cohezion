#!/usr/bin/env python3
"""Local Inference Multi-Perspective Adversarial Review for Inter-Daemon Loop Nexus.

Executes local adversarial audit via Lemonade (:13305) `gpt-oss-20b-mxfp4-GGUF`
evaluating:
1. Deadlock & Cascade Storm Vectors across daemon loops.
2. EventBus serialization overhead & unhandled exception propagation.
3. Memory growth & queue leak hazards under long-horizon execution.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LOCAL_AUDIT] %(message)s")
logger = logging.getLogger("local_audit")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
TARGET_FILE = "src/cohezion/compound/inter_daemon_loop_nexus.py"

LOCAL_PERSPECTIVES = [
    {
        "name": "Kernel & Resource Architect",
        "stance": "UMA Memory, File Descriptors, and Task Leak Specialist",
        "system": "You are a cynical kernel architect auditing async Python daemon loops. Look for unbounded in-memory lists, missing task cancellation, and memory leaks."
    },
    {
        "name": "Distributed Concurrency Lead",
        "stance": "Deadlock & Event Cascade Hunter",
        "system": "You are a distributed concurrency engineer looking for circular event deadlocks, feedback storm risks, and unhandled async exceptions in closed loop topologies."
    },
    {
        "name": "Frontier Reliability Engineer",
        "stance": "Fault Tolerance & Long-Horizon Self-Healing Lead",
        "system": "You are a reliability engineer auditing multi-daemon self-healing, graceful degradation, and event bus heartbeat timeouts."
    }
]

async def audit_with_local_model(target_code: str, perspective: dict[str, str]) -> dict[str, Any]:
    prompt = f"""Adversarially review this Inter-Daemon Loop Nexus implementation from your perspective ({perspective['stance']}).
State:
1. Verdict: [CLEAN / FINDINGS]
2. Critical Risk Score: [0-10]
3. Key Strengths & Vulnerabilities (2-3 concise, dense sentences):

```python
{target_code[:3000]}
```"""

    payload = {
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "messages": [
            {"role": "system", "content": perspective["system"]},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(LEMONADE_URL, json=payload)
        dt_s = time.perf_counter() - t0
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"].strip()
            return {
                "persona": perspective["name"],
                "stance": perspective["stance"],
                "latency_sec": round(dt_s, 2),
                "review": content
            }
        return {
            "persona": perspective["name"],
            "stance": perspective["stance"],
            "latency_sec": round(dt_s, 2),
            "review": f"HTTP Error {r.status_code}: {r.text}"
        }

async def run_local_review():
    print("\n" + "=" * 105)
    print("⚔️ LOCAL SILICON MULTI-PERSPECTIVE ADVERSARIAL REVIEW (:13305 Lemonade)")
    print(f"📂 Target: {TARGET_FILE}")
    print("=" * 105)

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    results = []
    for pers in LOCAL_PERSPECTIVES:
        res = await audit_with_local_model(code, pers)
        results.append(res)
        summary = res["review"].replace("\n", " ")[:110]
        print(f"\n• [{res['persona']}] ({res['latency_sec']}s)")
        print(f"  Stance : {res['stance']}")
        print(f"  Review : {summary}...")

    print("\n" + "=" * 105)
    print("🎉 LOCAL SILICON MULTI-PERSPECTIVE ADVERSARIAL AUDIT COMPLETE")
    print("=" * 105 + "\n")

    out_path = "docs/research/local_daemon_loops_adversarial_review.json"
    os.makedirs("docs/research", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved local review to %s", out_path)

if __name__ == "__main__":
    asyncio.run(run_local_review())
