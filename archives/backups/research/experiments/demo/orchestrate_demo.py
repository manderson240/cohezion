"""Live demo of TieredOrchestrator against the live fleet.

Exercises the AMD-optimized hierarchy (NPU → iGPU → CPU) — no cloud tier —
to prove that an agent can propose an action on the cheapest available lane
and have the orchestrator escalate silently if the quality gate fails.
"""

from __future__ import annotations

import asyncio

from cohezion.inference.gaia_adapter import amd_optimized_hierarchy


async def main() -> int:
    # max_cost_usd=0.0 → strict "no paid cloud" (local lanes at $0 still run).
    # Loosening the min_chars gates so one-word answers (like "proceed") pass.
    from cohezion.inference.orchestrator import QualityGate, TieredOrchestrator

    orch = TieredOrchestrator(
        tiers=[
            ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=3)),
            ("Gemma-4-E4B-it-GGUF", QualityGate(min_chars=3)),
            ("Gemma-4-26B-A4B-it-GGUF", QualityGate(min_chars=3)),
            ("Gemma-4-31B-it-GGUF", QualityGate(min_chars=3)),
        ],
        max_cost_usd=0.0,
        # Non-streaming dispatch for the demo — reasoning-mode FLM models
        # (Gemma-4 family) emit all tokens through reasoning_content until
        # the reasoning phase finishes, so streaming with small max_tokens
        # can return empty visible text. Non-streaming waits for the full
        # response, which always contains a visible answer.
        # For TTFT measurement specifically, use stream=True with max_tokens≥256.
        stream=False,
        # Gemma-4 reasoning-mode models (FLM backend) emit ~150-300 tokens
        # of internal thinking before visible content. 1024 is the safe floor
        # where the model reliably finishes reasoning (finish_reason="stop")
        # rather than truncating (finish_reason="length") with empty output.
        # See local_environment_quirks.md — "Reasoning-mode token budget".
        max_tokens=1024,
    )
    # Reference to keep the import used when user passes --default:
    _ = amd_optimized_hierarchy
    print(f"Hierarchy: {len(orch.tiers)} tiers (AMD-optimized, cloud excluded)")
    for i, (target, gate) in enumerate(orch.tiers):
        print(f"  tier {i}: {target}  gate_min_chars={gate.min_chars}")
    print()

    r = await orch.run("Reply in one word: proceed or rollback.")

    print(f"Primary:       {r.primary_model}")
    print(f"Final:         {r.final_model}")
    print(f"Escalations:   {r.escalation_count}")
    print(f"Cost:          ${r.cost_usd:.5f}")
    print(f"Latency:       {r.latency_ms:.0f}ms")
    print(f"TTFT:          {r.ttft_ms}ms" if r.ttft_ms else "TTFT:          n/a")
    print(f"Error:         {r.error}")
    print(f"Text:          {r.text[:100]!r}")
    print()
    print("Tier path:")
    for a in r.tier_path:
        print(
            f"  tier {a.tier_index} ({a.model_or_sub}): "
            f"passed={a.passed}  reason={a.reason}  "
            f"${a.cost_usd:.5f}  {a.latency_ms:.0f}ms"
        )
    return 0 if r.error is None else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
