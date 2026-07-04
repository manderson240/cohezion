"""Verify the full NPU→iGPU→CPU compound loop cascade.

Gate calibration (2026-06-25):
  Tier 0 NPU  (deepseek-r1, 512 tok):  max ~2232 chars → gate=2500 → ALWAYS escalates
  Tier 1 iGPU (Gemma-4-E4B, 2048 tok): max ~6522 chars → gate=7000 → ALWAYS escalates
  Tier 2 CPU  (Gemma-4-31B, 6144 tok): TRUST           → final answer

Usage:
  uv run python scripts/verify_cascade.py
"""

import asyncio
import sys
import time

from cohezion.inference.triune_orchestrator import build_reasoning_orchestrator


TASK = (
    "Design a complete production-grade session management system for a distributed compound AI "
    "orchestration platform. Cover: (1) session lifecycle (create, resume, expire, gc), "
    "(2) cross-node state synchronization with SurrealDB bi-temporal schemas, "
    "(3) token budget tracking across NPU/iGPU/CPU tiers, "
    "(4) security model (auth, isolation, rate-limits), "
    "(5) observability (metrics, degradation alerts, replay), and "
    "(6) failure recovery (checkpoint/rollback, partial-failure semantics). "
    "Include API signatures, data-flow diagrams in ASCII, and concrete implementation notes "
    "for each component. Be thorough — aim for a complete engineering spec."
)


async def run_cascade():
    print("Building reasoning orchestrator (NPU→iGPU→CPU via OmniRouter :13305)...")
    orch = build_reasoning_orchestrator()

    print(f"\nTask ({len(TASK)} chars):\n  {TASK[:120]}...\n")
    print("Starting cascade — watch escalation_count to confirm all tiers fire.\n")

    t0 = time.monotonic()
    result = await orch.run(TASK)
    elapsed = time.monotonic() - t0

    print("=" * 70)
    print(f"  Final model   : {result.final_model}")
    print(f"  Primary model : {result.primary_model}")
    print(f"  Escalations   : {result.escalation_count}  (expect 2 for full cascade)")
    print(f"  Output chars  : {len(result.text or '')}")
    print(f"  Latency       : {elapsed:.1f}s")
    print(f"  Cost          : ${result.cost_usd:.4f}")
    print("=" * 70)

    if result.escalation_count < 2:
        print(
            "\nWARN: expected escalation_count=2 (all 3 tiers), "
            f"got {result.escalation_count}. "
            "A tier may have been skipped — check Lemonade logs."
        )
        return False

    print("\nPASS: full NPU→iGPU→CPU cascade confirmed.")
    return True


if __name__ == "__main__":
    ok = asyncio.run(run_cascade())
    sys.exit(0 if ok else 1)
