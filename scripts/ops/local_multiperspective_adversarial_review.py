#!/usr/bin/env python3
"""Multi-Perspective Adversarial Review by Local Silicon Inference.

Dispatches structured adversarial review prompts to resident local model (`Qwen3-Coder-30B-A3B-Instruct-GGUF` / :13305).
Adversarial Personas:
1. Persona 1: Cynical AMD Strix Halo Hardware/Kernel Architect (Memory bus contention, iGPU aperture races, OOM causes).
2. Persona 2: Formal Verification & AutoHarness Lead (AST invariants, ZKFV soundness, false positive risks).
3. Persona 3: Swarm Distributed Systems Orchestrator (DataMesh consistency, EventBus deadlocks, cross-session races).
4. Persona 4: Sovereign Reliability & Production Chaos Engineer (Fail-closed guards, self-healing, post-OOM recovery).

Synthesis: Generates structured, prioritized attack vectors and concrete mitigations into `docs/research/local_silicon_multiperspective_adversarial_review.md`.
"""

from __future__ import annotations
import asyncio
import os
import time
import httpx
from pathlib import Path

os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference.smart_oom_governor import SmartOOMGovernor, CrossSessionFleetLock

LEMONADE_BASE = "http://localhost:13305"
OUT_PATH = Path("docs/research/local_silicon_multiperspective_adversarial_review.md")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

PROMPT = """You are conducting an exhaustive, multi-perspective adversarial review of the Cohezion sovereign AI platform on an AMD Strix Halo APU (128GB unified memory, Radeon 8060S iGPU, XDNA2 NPU).

The system recently experienced an OOM recovery event and operates under:
- `SmartOOMGovernor` (35.0 GiB safety floor).
- `CrossSessionFleetLock` (`/tmp/cohezion_fleet_modelload.lock`).
- `Z-Image-Turbo-TheNoise` local C++ ROCm diffusion engine (1024x1024).
- 8-agent DataMesh on SurrealDB (:8001) with EventBus cross-session bridges.
- AutoHarness zero-cost bytecode verification & 12D Poincaré manifold tracking.

Conduct an unsparing, highly technical adversarial review from 4 distinct personas:

### Persona 1: Cynical AMD Strix Halo Hardware / Kernel Architect
- Attack the unified memory architecture (UMA) contention between NPU compute-bound prefilling, iGPU C++ diffusion allocations, and CPU system daemons.
- Identify the exact root cause vectors of recurring OOM crashes on 128GB unified RAM and why 35 GiB thresholds can be breached during concurrent batch allocations.

### Persona 2: Formal Verification & AST Policy Lead
- Scrutinize the AutoHarness zero-cost bytecode action verifiers and Poincaré metric boundaries.
- Where can numerical instability, floating-point drift, or boundary edge cases ($\|x\| \to 1^-$) cause silent bypasses or crashes?

### Persona 3: Swarm Distributed Systems Orchestrator
- Critique the 8-Agent DataMesh, SurrealDB live query bridges, and EventBus routing.
- Identify lock contention, socket exhaustion, stale session ghost events, or deadlocks when daemons restart post-OOM.

### Persona 4: Sovereign Reliability & Production Chaos Engineer
- Stress-test the system's "Self-Healing" and recovery protocols.
- Detail the Top 3 highest-priority architectural hardening fixes required to guarantee zero unmanaged crashes during 24/7 autonomous runs.

Conclude with a consolidated, prioritized remediation matrix.
"""


async def run_review():
    print("\n" + "=" * 115)
    print("⚔️ MULTI-PERSPECTIVE ADVERSARIAL REVIEW VIA LOCAL SILICON INFERENCE")
    print("=" * 115)

    # 1. System Memory Check
    avail_gib, swap_used_gib, is_safe = SmartOOMGovernor.get_memory_state()
    print(f"\n▶ [1/3] Memory Preflight:")
    print(f"   • UMA Available:  {avail_gib} GiB (Floor: 35.0 GiB)")
    print(f"   • Swap Used:      {swap_used_gib} GiB")
    print(f"   • Status:         {'SAFE' if is_safe else 'BACKPRESSURE'}")

    # 2. Acquire FleetLock and Dispatch to Local Model
    print(
        f"\n▶ [2/3] Acquiring FleetLock & Dispatching to `Qwen3-Coder-30B-A3B-Instruct-GGUF` (:13305)..."
    )
    payload = {
        "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "messages": [
            {
                "role": "system",
                "content": "You are a ruthless, world-class adversarial systems auditor.",
            },
            {"role": "user", "content": PROMPT},
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
    }

    t0 = time.perf_counter()
    with CrossSessionFleetLock(timeout_sec=30.0):
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{LEMONADE_BASE}/v1/chat/completions", json=payload)
            dt = round(time.perf_counter() - t0, 2)
            if r.status_code == 200:
                data = r.json()
                msg = data["choices"][0]["message"]
                reasoning = msg.get("reasoning_content") or ""
                content = msg.get("content") or ""

                report = f"# Multi-Perspective Adversarial Review (Local Silicon)\n\n"
                report += (
                    f"**Auditor Model**: `Qwen3-Coder-30B-A3B-Instruct-GGUF` on AMD Strix Halo\n"
                )
                report += f"**Review Latency**: {dt}s | **Memory Headroom**: {avail_gib} GiB | **Tokens Generated**: ~{len((reasoning + content).split())} words\n\n"
                if reasoning:
                    report += (
                        f"## Chain-of-Thought Internal Audit (<think>)\n\n{reasoning}\n\n---\n\n"
                    )
                report += f"## Adversarial Findings & Remediation Matrix\n\n{content}\n"

                OUT_PATH.write_text(report)
                print(f"   ✓ Adversarial Review Completed in {dt}s!")
                print(f"   • Rendered Words: {len((reasoning + content).split())} words")
                print(f"   ✓ Saved report to `{OUT_PATH}`")
            else:
                print(f"   ❌ Review failed with HTTP {r.status_code}: {r.text[:200]}")
                return

    # 3. Publish to EventBus & SurrealDB DataMesh
    print(f"\n▶ [3/3] Emitting Telemetry to EventBus DataMesh...")
    event_bus = await get_event_bus()
    session_id = "adversarial_review_session"
    bridge = CrossSessionEventBridge(event_bus=event_bus, session_id=session_id)
    await bridge.initialize()

    ev = Event(
        type=EventType.CUSTOM,
        source="local_adversarial_auditor",
        priority=20,
        payload={
            "topic": "Multi-Perspective Adversarial Review",
            "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "duration_sec": dt,
            "report_path": str(OUT_PATH),
            "headroom_gib": avail_gib,
            "status": "AUDIT_COMPLETE",
        },
    )
    await event_bus.publish(ev)

    persist_item(
        {
            "id": "local_adversarial_review_complete",
            "title": "Local Silicon Multi-Perspective Adversarial Review Complete",
            "status": "done",
            "priority": "highest",
            "source": "local_adversarial_auditor",
            "category": "adversarial_audit",
            "details": f"4-persona adversarial review completed in {dt}s on Qwen3-Coder-30B. Report in {OUT_PATH}.",
        }
    )
    print("   ✓ Dual-persisted Kanban card to SurrealDB and Obsidian Vault!")

    print("\n" + "=" * 115)
    print("🏆 LOCAL SILICON ADVERSARIAL REVIEW COMPLETED & PERSISTED!")
    print("=" * 115 + "\n")


if __name__ == "__main__":
    asyncio.run(run_review())
