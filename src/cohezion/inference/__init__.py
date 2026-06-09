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

Lane layout (router-centric topology, Phase 2+):

All local lemonade models are served through the unified router at :13305.
The router dispatches to the appropriate backend on demand.

- Router (unified)    :13305  NPU / iGPU / CPU  all lemonade models
- Ollama local        :11434  phi4, qwen3-coder, deepseek-r1  (Phase 4 migration)  # allow-direct-port: Ollama models, Class A migration deferred to Phase 4
- Ollama cloud        :11434  deepseek-v3.2, gemini-3-flash  # allow-direct-port: Ollama cloud models, Class A migration deferred to Phase 4
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
from cohezion.inference.gaia_adapter import (
    GaiaAgentTier,
    build_gaia_mcp_tier,
    build_gaia_native_tier,
)
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
from cohezion.inference.router_client import LemonadeRouterClient
from cohezion.inference.unified_orchestrator import (
    UnifiedOrchestrator,
    create_default_orchestrator,
)


__all__ = [
    "FleetHealth",
    "FleetRegistry",
    "GaiaAgentTier",
    "Harness",
    "HarnessPool",
    "Lane",
    "LaneHealth",
    "LaneStatus",
    "LemonadeRouterClient",
    "ModelEntry",
    "OrchestrationResult",
    "QualityGate",
    "RouteResult",
    "Task",
    "TierAttempt",
    "TieredOrchestrator",
    "UnifiedOrchestrator",
    "build_gaia_mcp_tier",
    "build_gaia_native_tier",
    "check_fleet",
    "create_default_orchestrator",
    "default_hierarchy",
    "dispatch_through_harness",
    "extend_claude",
    "format_fleet_summary",
    "get_pool",
    "get_registry",
    "integrate_omnibus_gateways",
    "route",
]
