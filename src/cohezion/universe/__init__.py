"""Universe simulation engine and sandbox isolation.

Provides 12D/2048D manifold simulation, containerized code execution,
multi-backend sandbox isolation, divergence detection, agentic task
environments, capability evaluation, and experiment tracking.
"""

import contextlib

from cohezion.universe.agentic_env import (
    AgenticEnvironment,
    TaskScenario,
    ToolRegistry,
    TrajectoryRecorder,
)
from cohezion.universe.capability_eval import (
    EvalRunner,
    EvalScorer,
    RegressionDetector,
    TaskSuite,
    build_core_capability_suite,
)
from cohezion.universe.divergence import DivergenceDetector, DivergenceStatus
from cohezion.universe.engine import UniverseSimulationEngine
from cohezion.universe.example_simulations import EXAMPLES
from cohezion.universe.experiment_tracker import (
    ExperimentTracker,
    RunConfig,
)
from cohezion.universe.sandbox import ContainerizedUniverse, SandboxResult
from cohezion.universe.sandbox_backends import (
    BackendResult,
    DockerBackend,
    IsolationBackend,
    SubprocessBackend,
    SystemdRunBackend,
    select_backend,
)
from cohezion.universe.sandbox_manager import SandboxManager, get_sandbox_manager
from cohezion.universe.sandbox_profiles import (
    PROFILES,
    SandboxProfile,
    SandboxTier,
    get_profile,
)
from cohezion.universe.sandbox_results import persist_result


__all__ = [
    "EXAMPLES",
    "PROFILES",
    "AgenticEnvironment",
    "BackendResult",
    "ContainerizedUniverse",
    "DivergenceDetector",
    "DivergenceStatus",
    "DockerBackend",
    "EvalRunner",
    "EvalScorer",
    "ExperimentTracker",
    "IsolationBackend",
    "RegressionDetector",
    "RunConfig",
    "SandboxManager",
    "SandboxProfile",
    "SandboxResult",
    "SandboxTier",
    "SubprocessBackend",
    "SystemdRunBackend",
    "TaskScenario",
    "TaskSuite",
    "ToolRegistry",
    "TrajectoryRecorder",
    "UniverseSimulationEngine",
    "build_core_capability_suite",
    "get_profile",
    "get_sandbox_manager",
    "persist_result",
    "select_backend",
]

# ---------------------------------------------------------------------------
# Wiring-sweep 2026-06-22: orphan modules wired non-destructively
# ---------------------------------------------------------------------------

# Wiring-sweep 2026-06-22: advanced_components.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.advanced_components import (
        BioelectricsEngine as BioelectricsEngine,
        EsotericPhysicsEngine as EsotericPhysicsEngine,
        KordylewskiSwarmEngine as KordylewskiSwarmEngine,
        PenroseTwistorEngine as PenroseTwistorEngine,
        PlasmaMCPEngine as PlasmaMCPEngine,
        QuantumEmergenceEngine as QuantumEmergenceEngine,
        SacredGeometryEngine as SacredGeometryEngine,
    )

# Wiring-sweep 2026-06-22: adversarial_grounding.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.adversarial_grounding import (
        AdversarialGrounding as AdversarialGrounding,
        HallucinationAlert as HallucinationAlert,
        PerturbationResult as PerturbationResult,
    )

# Wiring-sweep 2026-06-22: agentic_evo_mhd.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.agentic_evo_mhd import (
        AgenticEVOMHD as AgenticEVOMHD,
        AgenticMHDSystem as AgenticMHDSystem,
        EVOMagneticState as EVOMagneticState,
        IonizationState as IonizationState,
        MHDField as MHDField,
    )

# Wiring-sweep 2026-06-22: agentic_evo_swift.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.agentic_evo_swift import (
        AgenticEVO as AgenticEVO,
        AgenticEVOSimulation as AgenticEVOSimulation,
        EVOCoupling as EVOCoupling,
        EVOLatentState as EVOLatentState,
        EVOPhysicalState as EVOPhysicalState,
        VacuumCoherence as VacuumCoherence,
    )

# Wiring-sweep 2026-06-22: components.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.components import (
        CellularAutomataEngine as CellularAutomataEngine,
        CellularAutomataState as CellularAutomataState,
        ChaosTheoryEngine as ChaosTheoryEngine,
        ChaosTheoryParameters as ChaosTheoryParameters,
        EVOInitializationFactory as EVOInitializationFactory,
        EvoState as EvoState,
        HIHOStabilizationEngine as HIHOStabilizationEngine,
        MagnetohydrodynamicsEngine as MagnetohydrodynamicsEngine,
    )

# Wiring-sweep 2026-06-22: evo_simulation.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.evo_simulation import (
        EVOSimulation as EVOSimulation,
        ExoticVacuumObject as ExoticVacuumObject,
        FLUMEJourneyStream as FLUMEJourneyStream,
        JourneyEvent as JourneyEvent,
        VAIEMetrics as VAIEMetrics,
        VacuumState as VacuumState,
    )

# Wiring-sweep 2026-06-22: factory.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.factory import (
        Universe as Universe,
        UniverseFactory as UniverseFactory,
        UniverseSpec as UniverseSpec,
    )

# Wiring-sweep 2026-06-22: freeze_frame.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.freeze_frame import (
        FreezeFrame as FreezeFrame,
        FreezeFrameCapture as FreezeFrameCapture,
        FreezeFrameStore as FreezeFrameStore,
    )

# Wiring-sweep 2026-06-22: hiho_unified_engine.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.hiho_unified_engine import (
        HIHOUnifiedEngine as HIHOUnifiedEngine,
    )

# Wiring-sweep 2026-06-22: intent_action_sync.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.intent_action_sync import (
        IntentActionPair as IntentActionPair,
        IntentActionSync as IntentActionSync,
        SyncVerdict as SyncVerdict,
    )

# Wiring-sweep 2026-06-22: intent_capture.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.intent_capture import (
        CheckResult as CheckResult,
        IntentCapture as IntentCapture,
        IntentPayload as IntentPayload,
        IntentViolation as IntentViolation,
        StateChangeRequest as StateChangeRequest,
    )

# Wiring-sweep 2026-06-22: llm_training_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.llm_training_bridge import (
        AgentTrajectory as AgentTrajectory,
        ExperienceDataset as ExperienceDataset,
        JudgmentAssessment as JudgmentAssessment,
        JudgmentEvaluator as JudgmentEvaluator,
        PreferencePair as PreferencePair,
        PreferencePairGenerator as PreferencePairGenerator,
        TokenReward as TokenReward,
        TrajectoryStep as TrajectoryStep,
        TrajectoryToReward as TrajectoryToReward,
    )

# Wiring-sweep 2026-06-22: schema.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.schema import (
        LOCAL_SCHEMA as LOCAL_SCHEMA,
        MIGRATIONS as MIGRATIONS,
        UNIVERSE_SCHEMA as UNIVERSE_SCHEMA,
    )

# Wiring-sweep 2026-06-22: spatial_phonons.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.spatial_phonons import (
        PhononParameters as PhononParameters,
        SpatialPhononsEngine as SpatialPhononsEngine,
    )

# Wiring-sweep 2026-06-22: triune_engine.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.triune_engine import (
        TriuneSimulationEngine as TriuneSimulationEngine,
    )

# Wiring-sweep 2026-06-22: triune_manifold.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.triune_manifold import (
        TriuneState as TriuneState,
        calculate_hiho_coherence as calculate_hiho_coherence,
        compute_restoring_force as compute_restoring_force,
    )

# Wiring-sweep 2026-06-22: truth_anchor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.truth_anchor import (
        CoherenceBubble as CoherenceBubble,
        RestoringForceResult as RestoringForceResult,
        TruthAnchor as TruthAnchor,
        TruthAnchorValidator as TruthAnchorValidator,
        ValidationResult as ValidationResult,
    )

# Wiring-sweep 2026-06-22: viz_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.viz_bridge import (
        VisualizationBridge as VisualizationBridge,
    )
