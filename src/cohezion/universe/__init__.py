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
    )
    from cohezion.universe.advanced_components import (
        EsotericPhysicsEngine as EsotericPhysicsEngine,
    )
    from cohezion.universe.advanced_components import (
        KordylewskiSwarmEngine as KordylewskiSwarmEngine,
    )
    from cohezion.universe.advanced_components import (
        PenroseTwistorEngine as PenroseTwistorEngine,
    )
    from cohezion.universe.advanced_components import (
        PlasmaMCPEngine as PlasmaMCPEngine,
    )
    from cohezion.universe.advanced_components import (
        QuantumEmergenceEngine as QuantumEmergenceEngine,
    )
    from cohezion.universe.advanced_components import (
        SacredGeometryEngine as SacredGeometryEngine,
    )

# Wiring-sweep 2026-06-22: adversarial_grounding.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.adversarial_grounding import (
        AdversarialGrounding as AdversarialGrounding,
    )
    from cohezion.universe.adversarial_grounding import (
        HallucinationAlert as HallucinationAlert,
    )
    from cohezion.universe.adversarial_grounding import (
        PerturbationResult as PerturbationResult,
    )

# Wiring-sweep 2026-06-22: agentic_evo_mhd.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.agentic_evo_mhd import (
        AgenticEVOMHD as AgenticEVOMHD,
    )
    from cohezion.universe.agentic_evo_mhd import (
        AgenticMHDSystem as AgenticMHDSystem,
    )
    from cohezion.universe.agentic_evo_mhd import (
        EVOMagneticState as EVOMagneticState,
    )
    from cohezion.universe.agentic_evo_mhd import (
        IonizationState as IonizationState,
    )
    from cohezion.universe.agentic_evo_mhd import (
        MHDField as MHDField,
    )

# Wiring-sweep 2026-06-22: agentic_evo_swift.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.agentic_evo_swift import (
        AgenticEVO as AgenticEVO,
    )
    from cohezion.universe.agentic_evo_swift import (
        AgenticEVOSimulation as AgenticEVOSimulation,
    )
    from cohezion.universe.agentic_evo_swift import (
        EVOCoupling as EVOCoupling,
    )
    from cohezion.universe.agentic_evo_swift import (
        EVOLatentState as EVOLatentState,
    )
    from cohezion.universe.agentic_evo_swift import (
        EVOPhysicalState as EVOPhysicalState,
    )
    from cohezion.universe.agentic_evo_swift import (
        VacuumCoherence as VacuumCoherence,
    )

# Wiring-sweep 2026-06-22: components.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.components import (
        CellularAutomataEngine as CellularAutomataEngine,
    )
    from cohezion.universe.components import (
        CellularAutomataState as CellularAutomataState,
    )
    from cohezion.universe.components import (
        ChaosTheoryEngine as ChaosTheoryEngine,
    )
    from cohezion.universe.components import (
        ChaosTheoryParameters as ChaosTheoryParameters,
    )
    from cohezion.universe.components import (
        EVOInitializationFactory as EVOInitializationFactory,
    )
    from cohezion.universe.components import (
        EvoState as EvoState,
    )
    from cohezion.universe.components import (
        HIHOStabilizationEngine as HIHOStabilizationEngine,
    )
    from cohezion.universe.components import (
        MagnetohydrodynamicsEngine as MagnetohydrodynamicsEngine,
    )

# Wiring-sweep 2026-06-22: evo_simulation.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.evo_simulation import (
        EVOSimulation as EVOSimulation,
    )
    from cohezion.universe.evo_simulation import (
        ExoticVacuumObject as ExoticVacuumObject,
    )
    from cohezion.universe.evo_simulation import (
        FLUMEJourneyStream as FLUMEJourneyStream,
    )
    from cohezion.universe.evo_simulation import (
        JourneyEvent as JourneyEvent,
    )
    from cohezion.universe.evo_simulation import (
        VacuumState as VacuumState,
    )
    from cohezion.universe.evo_simulation import (
        VAIEMetrics as VAIEMetrics,
    )

# Wiring-sweep 2026-06-22: factory.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.factory import (
        Universe as Universe,
    )
    from cohezion.universe.factory import (
        UniverseFactory as UniverseFactory,
    )
    from cohezion.universe.factory import (
        UniverseSpec as UniverseSpec,
    )

# Wiring-sweep 2026-06-22: freeze_frame.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.freeze_frame import (
        FreezeFrame as FreezeFrame,
    )
    from cohezion.universe.freeze_frame import (
        FreezeFrameCapture as FreezeFrameCapture,
    )
    from cohezion.universe.freeze_frame import (
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
    )
    from cohezion.universe.intent_action_sync import (
        IntentActionSync as IntentActionSync,
    )
    from cohezion.universe.intent_action_sync import (
        SyncVerdict as SyncVerdict,
    )

# Wiring-sweep 2026-06-22: intent_capture.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.intent_capture import (
        CheckResult as CheckResult,
    )
    from cohezion.universe.intent_capture import (
        IntentCapture as IntentCapture,
    )
    from cohezion.universe.intent_capture import (
        IntentPayload as IntentPayload,
    )
    from cohezion.universe.intent_capture import (
        IntentViolation as IntentViolation,
    )
    from cohezion.universe.intent_capture import (
        StateChangeRequest as StateChangeRequest,
    )

# Wiring-sweep 2026-06-22: llm_training_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.llm_training_bridge import (
        AgentTrajectory as AgentTrajectory,
    )
    from cohezion.universe.llm_training_bridge import (
        ExperienceDataset as ExperienceDataset,
    )
    from cohezion.universe.llm_training_bridge import (
        JudgmentAssessment as JudgmentAssessment,
    )
    from cohezion.universe.llm_training_bridge import (
        JudgmentEvaluator as JudgmentEvaluator,
    )
    from cohezion.universe.llm_training_bridge import (
        PreferencePair as PreferencePair,
    )
    from cohezion.universe.llm_training_bridge import (
        PreferencePairGenerator as PreferencePairGenerator,
    )
    from cohezion.universe.llm_training_bridge import (
        TokenReward as TokenReward,
    )
    from cohezion.universe.llm_training_bridge import (
        TrajectoryStep as TrajectoryStep,
    )
    from cohezion.universe.llm_training_bridge import (
        TrajectoryToReward as TrajectoryToReward,
    )

# Wiring-sweep 2026-06-22: schema.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.schema import (
        LOCAL_SCHEMA as LOCAL_SCHEMA,
    )
    from cohezion.universe.schema import (
        MIGRATIONS as MIGRATIONS,
    )
    from cohezion.universe.schema import (
        UNIVERSE_SCHEMA as UNIVERSE_SCHEMA,
    )

# Wiring-sweep 2026-06-22: spatial_phonons.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.spatial_phonons import (
        PhononParameters as PhononParameters,
    )
    from cohezion.universe.spatial_phonons import (
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
    )
    from cohezion.universe.triune_manifold import (
        calculate_hiho_coherence as calculate_hiho_coherence,
    )
    from cohezion.universe.triune_manifold import (
        compute_restoring_force as compute_restoring_force,
    )

# Wiring-sweep 2026-06-22: truth_anchor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.truth_anchor import (
        CoherenceBubble as CoherenceBubble,
    )
    from cohezion.universe.truth_anchor import (
        RestoringForceResult as RestoringForceResult,
    )
    from cohezion.universe.truth_anchor import (
        TruthAnchor as TruthAnchor,
    )
    from cohezion.universe.truth_anchor import (
        TruthAnchorValidator as TruthAnchorValidator,
    )
    from cohezion.universe.truth_anchor import (
        ValidationResult as ValidationResult,
    )

# Wiring-sweep 2026-06-22: viz_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.universe.viz_bridge import (
        VisualizationBridge as VisualizationBridge,
    )
