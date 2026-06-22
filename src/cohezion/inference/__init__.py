"""Cohezion inference fleet — unified local-first routing.

Public API:

    from cohezion.inference import route, extend_claude, check_fleet

    # Basic routing
    result = await route("Summarize this PR...", task="summarization")

    # Extend Claude availability: try local first, escalate only if needed
    result = await extend_claude(prompt, claude_model="claude-sonnet-4-6")

    # Fleet status snapshot
    health = check_fleet()
    print(health.local_lanes_up, "local lanes up")

Lane layout (Strix Halo Symphony — see STRIX_HALO_SYMPHONY_GUIDE.md):

- NPU (XDNA 2)        :13306  Gemma-4-E2B     Sensing / Doer
- iGPU ROCWMMA        :13307  Gemma-4-E4B     Governance / Knower
- iGPU Unified        :13308  Gemma-4-26B-A4B Reasoning / Thinker  (MoE)
- CPU AVX-VNNI        :13309  Gemma-4-31B     Architect / Safety
- Ollama local        :11434  phi4, qwen3-coder, deepseek-r1
- Ollama cloud        :11434  deepseek-v3.2, gemini-3-flash
- Anthropic API       https://api.anthropic.com  claude-haiku|sonnet|opus

The ``turboquant_axis`` injection (SU(2) spinor coherence → KV cache rotation
axis) happens inside ``fleet.route()`` via ``SymmetryHardwareBridge``.
"""

import contextlib


# Wiring-sweep 2026-06-06: lynx_gate was a genuine import-graph orphan. Guarded re-export makes
# its escalation gate part of the inference surface + statically reachable (cycle-safe: lynx_gate
# imports no swarm/compound, unlike the swarm/ blockers).
with contextlib.suppress(Exception):
    from cohezion.inference.lynx_gate import (
        EscalationProbe as EscalationProbe,
    )
    from cohezion.inference.lynx_gate import (
        LYNXGate as LYNXGate,
    )

from cohezion.inference.fleet import RouteResult, extend_claude, route
from cohezion.inference.harnesses import (
    Harness,
    HarnessPool,
    dispatch_through_harness,
    get_pool,
)
from cohezion.inference.health import (
    FleetHealth,
    LaneHealth,
    LaneStatus,
    check_fleet,
    format_fleet_summary,
    integrate_omnibus_gateways,
)
from cohezion.inference.orchestrator import (
    OrchestrationResult,
    QualityGate,
    TierAttempt,
    TieredOrchestrator,
    default_hierarchy,
)
from cohezion.inference.registry import (
    FleetRegistry,
    Lane,
    ModelEntry,
    Task,
    get_registry,
)


__all__ = [
    "FleetHealth",
    "FleetRegistry",
    "Harness",
    "HarnessPool",
    "Lane",
    "LaneHealth",
    "LaneStatus",
    "ModelEntry",
    "OrchestrationResult",
    "QualityGate",
    "RouteResult",
    "Task",
    "TierAttempt",
    "TieredOrchestrator",
    "check_fleet",
    "default_hierarchy",
    "dispatch_through_harness",
    "extend_claude",
    "format_fleet_summary",
    "get_pool",
    "get_registry",
    "integrate_omnibus_gateways",
    "route",
]
