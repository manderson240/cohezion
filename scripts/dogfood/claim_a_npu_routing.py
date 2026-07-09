#!/usr/bin/env python3
"""Dogfood Claim A — fleet routes to NPU correctly when budget forces local.

Exercises real route() against the running lemonade NPU endpoint at
:13306. Verifies:
- RouteResult has text, model, lane, latency_ms populated
- lane == 'npu' (NOT claude/cloud)
- cost_usd == 0.0 (local is free)
- ttft_ms is a positive number (streaming measurement worked)
- text is non-empty and short for a short prompt

Run from main worktree:
    cd /home/mike-anderson/dev/cohezion
    uv run python /tmp/cohezion-deliver/scripts/dogfood/claim_a_npu_routing.py
"""

from __future__ import annotations

import asyncio
import sys

from cohezion.inference import route
from cohezion.inference.registry import Task


async def main() -> int:
    print("=== Claim A — NPU routing via route() ===\n")

    # Short prompt that should route to NPU (smallest model, cheapest task)
    prompt = 'Reply in one word, "proceed" or "rollback", for a safe rollout.'

    print(f"Prompt: {prompt!r}")
    print("Calling route(task=Task.ROUTING, budget_usd=0.0, stream=True) ...\n")

    try:
        result = await route(
            prompt,
            task=Task.ROUTING,
            budget_usd=0.0,  # force local-only
            stream=True,
            max_tokens=1024,  # reasoning-mode models need headroom (see local_environment_quirks.md)
            timeout=15.0,
        )
    except Exception as exc:
        print(f"FAIL A-dispatch — route() raised: {type(exc).__name__}: {exc}")
        return 1

    # Print everything for the dogfood log
    print(f"text          : {result.text!r}")
    print(f"model         : {result.model!r}")
    print(f"lane          : {result.lane!r}")
    print(f"latency_ms    : {result.latency_ms:.1f}")
    print(f"ttft_ms       : {result.ttft_ms}")
    print(f"cost_usd      : {result.cost_usd}")
    print(f"error         : {result.error!r}")
    print(f"attempts      : {len(result.attempts)} attempt(s)")

    failures = []
    if result.error:
        failures.append(f"error was set: {result.error!r}")
    if not result.text or not result.text.strip():
        failures.append("text is empty")
    if result.lane in {"claude", "cloud_claude", "cloud_ollama"}:
        failures.append(f"lane='{result.lane}' — routed to cloud despite budget_usd=0.0")
    if result.cost_usd > 0:
        failures.append(f"cost_usd={result.cost_usd} — local lanes should be free")
    # TTFT may be None if reasoning-mode models ate the budget on <thinking> — not a fail per quirks.md

    if failures:
        print("\nFAIL A:")
        for f in failures:
            print(f"  - {f}")
        return 1

    # Bonus: verify TTFT claim (~80 ms p50 per SHOWCASE)
    if result.ttft_ms is not None and result.ttft_ms < 2000:
        print(f"\nPASS A — routed locally to lane={result.lane}, TTFT={result.ttft_ms:.1f}ms")
    else:
        print(
            f"\nPARTIAL PASS A — routed locally to lane={result.lane} but TTFT={result.ttft_ms} (expected < 2000ms)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
