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

# Wiring-sweep 2026-06-22: task_classifier was a genuine import-graph orphan. Guarded re-export
# makes its zero-latency router part of the inference surface (CL1/CL2/CL3 harness invariants).
# `Harness` aliased `AgenticHarness` to avoid shadowing harnesses.Harness (process slots).
with contextlib.suppress(Exception):
    from cohezion.inference.task_classifier import Harness as AgenticHarness  # noqa: F401
    from cohezion.inference.task_classifier import (
        RouteDecision as RouteDecision,
    )
    from cohezion.inference.task_classifier import (
        band_for_node as band_for_node,
    )
    from cohezion.inference.task_classifier import (
        classify as classify,
    )
    from cohezion.inference.task_classifier import (
        classify_with_harness as classify_with_harness,
    )
    from cohezion.inference.task_classifier import (
        select_harness as select_harness,
    )

# Wiring-sweep 2026-06-22: confidence_calibration wires Platt-scaling on classify().confidence.
with contextlib.suppress(Exception):
    from cohezion.inference.confidence_calibration import (
        PlattCalibrator as PlattCalibrator,
    )
    from cohezion.inference.confidence_calibration import (
        calibrated_classify as calibrated_classify,
    )
    from cohezion.inference.confidence_calibration import (
        set_default_calibrator as set_default_calibrator,
    )

# Wiring-sweep 2026-06-22: anti_sycophancy — bias-resistant evaluation guard.
with contextlib.suppress(Exception):
    from cohezion.inference.anti_sycophancy import (
        AntiSycophancyGuard as AntiSycophancyGuard,
    )
    from cohezion.inference.anti_sycophancy import (
        SycophancyRisk as SycophancyRisk,
    )
    from cohezion.inference.anti_sycophancy import (
        create_sycophancy_resistant_runner as create_sycophancy_resistant_runner,
    )

# Wiring-sweep 2026-06-22: autoharness_ce — compound engineering autoharness.
with contextlib.suppress(Exception):
    from cohezion.inference.autoharness_ce import (
        CompoundEngineeringAutoHarness as CompoundEngineeringAutoHarness,
    )
    from cohezion.inference.autoharness_ce import (
        create_compound_autoharness as create_compound_autoharness,
    )

# Wiring-sweep 2026-06-22: context_engineering — model card registry + context engineer.
with contextlib.suppress(Exception):
    from cohezion.inference.context_engineering import (
        ContextEngineer as ContextEngineer,
    )
    from cohezion.inference.context_engineering import (
        ModelCard as ModelCard,
    )
    from cohezion.inference.context_engineering import (
        ModelCardRegistry as ModelCardRegistry,
    )
    from cohezion.inference.context_engineering import (
        get_context_engineer as get_context_engineer,
    )

# Wiring-sweep 2026-06-22: evaluation_harness — quality metrics and cost estimation.
with contextlib.suppress(Exception):
    from cohezion.inference.evaluation_harness import (
        EvaluationHarness as EvaluationHarness,
    )
    from cohezion.inference.evaluation_harness import (
        ExperimentMetrics as ExperimentMetrics,
    )
    from cohezion.inference.evaluation_harness import (
        evaluate_quality_simple as evaluate_quality_simple,
    )

# Wiring-sweep 2026-06-22: fractal_metrics — Higuchi FD, Feynman path weights (harness A3/CC1).
with contextlib.suppress(Exception):
    from cohezion.inference.fractal_metrics import (
        feynman_path_weight as feynman_path_weight,
    )
    from cohezion.inference.fractal_metrics import (
        higuchi_fd as higuchi_fd,
    )
    from cohezion.inference.fractal_metrics import (
        quality_series_report as quality_series_report,
    )

# Wiring-sweep 2026-06-22: gaia_adapter — AMD-optimized GAIA agent tier builder.
with contextlib.suppress(Exception):
    from cohezion.inference.gaia_adapter import (
        GaiaAgentTier as GaiaAgentTier,
    )
    from cohezion.inference.gaia_adapter import (
        build_gaia_native_tier as build_gaia_native_tier,
    )
    from cohezion.inference.gaia_adapter import (
        rank_models_by_amd_optimization as rank_models_by_amd_optimization,
    )

# Wiring-sweep 2026-06-22: hardware_telemetry — NPU/iGPU/CPU utilization snapshots.
with contextlib.suppress(Exception):
    from cohezion.inference.hardware_telemetry import (
        ComputeBackend as ComputeBackend,
    )
    from cohezion.inference.hardware_telemetry import (
        HardwareSnapshot as HardwareSnapshot,
    )
    from cohezion.inference.hardware_telemetry import (
        HardwareTelemetry as HardwareTelemetry,
    )
    from cohezion.inference.hardware_telemetry import (
        create_hardware_telemetry as create_hardware_telemetry,
    )

# Wiring-sweep 2026-06-22: oom_guard — RAM gate + ctx_size harden (harness N3).
with contextlib.suppress(Exception):
    from cohezion.inference.oom_guard import check_ram as check_ram
    from cohezion.inference.oom_guard import pre_load_gate as pre_load_gate
    from cohezion.inference.oom_guard import scan_and_harden as scan_and_harden

# Wiring-sweep 2026-06-22: orchestrator_autoharness — Strix Halo multi-node orchestrator.
with contextlib.suppress(Exception):
    from cohezion.inference.orchestrator_autoharness import (
        MultiNodeOrchestrator as MultiNodeOrchestrator,
    )
    from cohezion.inference.orchestrator_autoharness import (
        StrixHaloOrchestrator as StrixHaloOrchestrator,
    )
    from cohezion.inference.orchestrator_autoharness import (
        create_strix_halo_orchestrator as create_strix_halo_orchestrator,
    )

# Wiring-sweep 2026-06-22: p0_resilience_mixins — timeout, checkpoint, async executor mixins.
with contextlib.suppress(Exception):
    from cohezion.inference.p0_resilience_mixins import (
        AsyncExecutorMixin as AsyncExecutorMixin,
    )
    from cohezion.inference.p0_resilience_mixins import (
        CheckpointManager as CheckpointManager,
    )
    from cohezion.inference.p0_resilience_mixins import (
        HealthChecker as HealthChecker,
    )
    from cohezion.inference.p0_resilience_mixins import (
        TimeoutMixin as TimeoutMixin,
    )

# Wiring-sweep 2026-06-22: seed_evaluator — deterministic seed quality scoring.
with contextlib.suppress(Exception):
    from cohezion.inference.seed_evaluator import (
        eval_quality as eval_quality,
    )
    from cohezion.inference.seed_evaluator import (
        get_seed_analysis as get_seed_analysis,
    )
    from cohezion.inference.seed_evaluator import (
        select_best_seed as select_best_seed,
    )

# Wiring-sweep 2026-06-22: transition_controller — Markov state transition analysis.
with contextlib.suppress(Exception):
    from cohezion.inference.transition_controller import (
        TransitionController as TransitionController,
    )
    from cohezion.inference.transition_controller import (
        detect_stuck_loops as detect_stuck_loops,
    )
    from cohezion.inference.transition_controller import (
        first_passage as first_passage,
    )

# Wiring-sweep 2026-06-22: tri_compute_orchestrator — NPU/iGPU/CPU tri-compute engines.
with contextlib.suppress(Exception):
    from cohezion.inference.tri_compute_orchestrator import (
        CPUOrchestrationEngine as CPUOrchestrationEngine,
    )
    from cohezion.inference.tri_compute_orchestrator import (
        NPUInferenceEngine as NPUInferenceEngine,
    )
    from cohezion.inference.tri_compute_orchestrator import (
        iGPUSimulationEngine as iGPUSimulationEngine,
    )

# Wiring-sweep 2026-06-22: triune_orchestrator — three-tier local inference builder (harness N2).
with contextlib.suppress(Exception):
    from cohezion.inference.triune_orchestrator import (
        build_triune_orchestrator as build_triune_orchestrator,
    )

# Wiring-sweep 2026-06-22: turboquant_reference — Hadamard rotation + polar quantization.
with contextlib.suppress(Exception):
    from cohezion.inference.turboquant_reference import (
        HadamardRotation as HadamardRotation,
    )
    from cohezion.inference.turboquant_reference import (
        PolarQuant as PolarQuant,
    )
    from cohezion.inference.turboquant_reference import (
        TurboQuantReference as TurboQuantReference,
    )

# Wiring-sweep 2026-06-22: turboquant_streaming — KV cache compression for long contexts.
with contextlib.suppress(Exception):
    from cohezion.inference.turboquant_streaming import (
        KVCacheStats as KVCacheStats,
    )
    from cohezion.inference.turboquant_streaming import (
        StreamingKVCompressor as StreamingKVCompressor,
    )

# Wiring-sweep 2026-06-22: seed_evaluator — best-of-N seed selection for local inference.
with contextlib.suppress(Exception):
    from cohezion.inference.seed_evaluator import eval_quality as eval_quality
    from cohezion.inference.seed_evaluator import select_best_seed as select_best_seed

from cohezion.inference.fleet import RouteResult, extend_claude, route
from cohezion.inference.gaia_adapter import (
    GaiaAgentTier,
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
    "ModelEntry",
    "OrchestrationResult",
    "QualityGate",
    "RouteResult",
    "Task",
    "TierAttempt",
    "TieredOrchestrator",
    "UnifiedOrchestrator",
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
