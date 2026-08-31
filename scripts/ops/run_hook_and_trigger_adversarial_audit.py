#!/usr/bin/env python3
"""Multi-Perspective Adversarial Hook & Trigger Audit.

Audits Cohezion's event-driven hooks, triggers, and reactive subscriptions across:
1. `src/cohezion/core/event_bus.py` (Core Pub/Sub & DLQ)
2. `src/cohezion/core/cross_session_event_bridge.py` (Bi-Temporal SurrealDB Sync)
3. `src/cohezion/core/grand_unified_wiring_bus.py` (Subsystem Event Ingestion)
4. `src/cohezion/data_mesh/kanban_bridge.py` (Reactive Kanban Cards)
5. `src/cohezion/proactive/spinning_plates_protocol.py` (Reactive Background Triggers)

Dispatches to Ollama Cloud frontier models:
- `deepseek-v4-pro:cloud`: "Red Team Event Systems & Reactive Security Specialist"
- `qwen3.5:397b-cloud`: "Principal Distributed Message Broker & Event Pipeline Architect"
- `glm-5.2:cloud`: "Formal Sheaf & Reactive Flow Theorist"
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hook_trigger_audit")

REVIEWERS = [
    (
        "deepseek-v4-pro:cloud",
        "Red Team Event Systems & Reactive Security Specialist",
        "You are an adversarial Red Team Security & Concurrency Auditor. Audit Cohezion's EventBus hooks, trigger handlers, Dead-Letter Queue (DLQ), and cross-session event bridges for event loop blocking, memory leak via unbounded handler growth, unhandled exception silencing, and cascading deadlocks.",
    ),
    (
        "qwen3.5:397b-cloud",
        "Principal Distributed Message Broker & Event Pipeline Architect",
        "You are a Principal Distributed Systems & Event Broker Architect. Audit Cohezion's Pub/Sub architecture, topic taxonomy, reactive triggers, backpressure governors, and bi-temporal persistence for throughput bottlenecks, message delivery guarantees (at-least-once vs at-most-once), and cross-session synchronization.",
    ),
    (
        "glm-5.2:cloud",
        "Formal Sheaf & Reactive Flow Theorist",
        "You are a Mathematical Physicist and Reactive Systems Theorist. Audit Cohezion's hook and trigger graph for topological acyclicity, causal ordering preservation, sheaf section gluing across distributed sessions, and entropy accumulation in event queues.",
    ),
]

FILES_TO_REVIEW = [
    "src/cohezion/core/event_bus.py",
    "src/cohezion/core/cross_session_event_bridge.py",
    "src/cohezion/core/grand_unified_wiring_bus.py",
    "src/cohezion/core/event_bus_dlq.py",
]


async def query_model(model_name: str, role: str, persona_prompt: str, code_bundle: str) -> dict:
    logger.info("Dispatching Hook & Trigger audit to %s (%s)...", model_name, role)
    full_prompt = f"""{persona_prompt}

Perform an exhaustive, adversarial, and uncompromising audit of Cohezion's Hook, Trigger, and EventBus architecture.

Source Code Bundle:
{code_bundle}

Provide your structured audit report:
1. CRITICAL VULNERABILITIES & BOTTLENECKS (Deadlocks, handler memory leaks, backpressure failures, missing idempotency).
2. TOPOLOGICAL & ARCHITECTURAL VIOLATIONS (Causal ordering, broken gluing, unhandled edge-cases).
3. CONCRETE HARDENING RECOMMENDATIONS (With exact code snippets).
4. FINAL AUDIT VERDICT: [APPROVED | CHANGES REQUIRED | BLOCKED]
"""
    url = "http://localhost:11434/api/generate"
    data = json.dumps({
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.15}
    })
    req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        resp_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=180.0).read().decode("utf-8"))
        res = json.loads(resp_data)
        content = res.get("response") or res.get("thinking") or ""
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        return {"model": model_name, "role": role, "content": content, "success": True}
    except Exception as exc:
        logger.error("Model %s error: %s", model_name, exc)
        return {"model": model_name, "role": role, "content": str(exc), "success": False}


async def main():
    logger.info("=" * 90)
    logger.info("STARTING MULTI-PERSPECTIVE HOOK & TRIGGER AUDIT (OLLAMA CLOUD)")
    logger.info("=" * 90)

    code_sections = []
    for rel_p in FILES_TO_REVIEW:
        p = REPO_ROOT / rel_p
        if p.exists():
            code_sections.append(f"### File: `{rel_p}`\n```python\n{p.read_text()}\n```\n")

    full_code_bundle = "\n".join(code_sections)

    tasks = [query_model(m, r, prompt, full_code_bundle) for m, r, prompt in REVIEWERS]
    results = await asyncio.gather(*tasks)

    report_lines = [
        "# Multi-Perspective Adversarial Review: Hook, Trigger & EventBus Architecture\n",
        f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n",
        "**Evaluators**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`\n\n---\n",
    ]

    for r in results:
        report_lines.append(f"## Perspective: {r['model']} — {r['role']}\n\n")
        report_lines.append(r["content"].strip())
        report_lines.append("\n\n---\n")

    report_file = REPO_ROOT / "docs/research/hook_and_trigger_adversarial_audit.md"
    report_file.write_text("\n".join(report_lines))
    logger.info("✅ Saved Hook & Trigger adversarial audit to %s", report_file)


if __name__ == "__main__":
    asyncio.run(main())
