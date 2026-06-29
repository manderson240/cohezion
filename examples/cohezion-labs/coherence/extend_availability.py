"""Extend Claude availability via the local Lemonade fleet.

This example shows the canonical pattern for token-efficient agent execution:

1. Load a prompt.
2. Call ``extend_availability()`` from ``cohezion.agents.fleet_adapter``.
3. The local NPU/iGPU/CPU lanes on :13305 are tried first.
4. If local output is empty or below the quality gate, the call escalates to a
   named cloud/Ollama fallback model.
5. Telemetry (model used, lane, latency, escalation flag) is returned for the
   learning loop.

Usage::

    uv run examples/cohezion-labs/coherence/extend_availability.py "Summarize Cohezion"
"""

from __future__ import annotations

import asyncio
import sys

from cohezion.agents.fleet_adapter import call_local_first


async def extend_availability(
    prompt: str,
    *,
    fallback_model: str = "claude-sonnet-4-6",
    max_tokens: int = 512,
) -> str:
    """Run ``prompt`` through the local fleet first, escalate only if needed.

    Args:
        prompt: The task to perform.
        fallback_model: Cloud/Ollama model to use if local lanes fail.
        max_tokens: Output budget.

    Returns:
        Generated text (local or escalated).
    """
    result = await call_local_first(
        prompt,
        model=fallback_model,
        max_tokens=max_tokens,
        allow_cloud_fallback=True,
        timeout=30.0,
    )
    if result.get("error"):
        print(f"⚠️ Fleet error: {result['error']}", file=sys.stderr)
    print(f"model={result['model']} lane={result['lane']} "
          f"latency_ms={result['latency_ms']:.1f} "
          f"escalated={result['escalated_to_cloud']}")
    return result.get("text", "")


async def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "What is token-efficient compound engineering?"
    answer = await extend_availability(prompt)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
