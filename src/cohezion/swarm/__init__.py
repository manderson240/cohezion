"""Swarm orchestration and token-efficient inference."""

import contextlib

# Note: Some imports are currently broken due to missing modules.
# They are commented out to allow the rest of the codebase to function.
# TODO: Restore these imports once the underlying modules are implemented:
# - adaptive_router_adapter
# - hardware_profiler_stub
from cohezion.swarm.adaptive_router import (
    AdaptiveRouter,
    route_task,
)
from cohezion.swarm.adaptive_router import (
    RoutingDecision as AdaptiveRoutingDecision,
)
from cohezion.swarm.batch_processor import (
    BatchItem,
    BatchProcessor,
    BatchResult,
    CacheEntry,
)
from cohezion.swarm.compute_backend_router import (
    BackendCapability,
    BackendConstraints,
    BackendStatus,
    BackendType,
    ComputeBackendRouter,
    route_compute,
)
from cohezion.swarm.compute_backend_router import (
    RoutingDecision as BackendRoutingDecision,
)
from cohezion.swarm.dynamic_agent_registry import (
    AgentModule,
    DynamicAgentRegistry,
    get_global_registry,
)
from cohezion.swarm.hardware_aware_router import (
    Priority,
    RoutingDecision,
    RoutingRequest,
)
from cohezion.swarm.lru_persistent_cache import (
    LRUPersistentCache,
)
from cohezion.swarm.model_pool_config import (
    ModelTierPolicy,
    PooledModel,
    PoolStatus,
    TierConfig,
)
from cohezion.swarm.model_pool_manager import (
    ModelPoolManager,
    get_pool_manager,
    reset_pool_manager,
)
from cohezion.swarm.multi_agent_orchestrator import (
    ExecutionResult,
    MultiAgentOrchestrator,
    execute_task,
    get_orchestrator,
    quick_orchestrate,
)
from cohezion.swarm.multi_layer_cache import (
    CacheEntry as MultiLayerCacheEntry,
)
from cohezion.swarm.multi_layer_cache import (
    ContextPoolManager,
    KVCacheOptimizer,
    MultiLayerCache,
    SemanticCacheStore,
)
from cohezion.swarm.persistent_cache import (
    PersistentCache,
    get_persistent_cache,
)

# from cohezion.swarm.dynamic_concurrency_gate import (
#     DynamicConcurrencyGate,
#     get_concurrency_gate,
# )
from cohezion.swarm.persistent_token_cache import (
    PersistentTokenCache,
)

# Multi-agent orchestration (dynamic + adaptive)
from cohezion.swarm.specialist_agents import (
    CODE_SPECIALIST,
    NOVEL_SPECIALIST,
    REASONING_SPECIALIST,
    VALIDATED_SPECIALISTS,
    SpecialistAgent,
    ToolRegistry,
    get_specialist,
    list_validated_specialists,
)
from cohezion.swarm.token_cache_optimizer import (
    CacheOptimizationConfig,
    TokenCacheOptimizer,
    get_token_cache_optimizer,
)
from cohezion.swarm.token_client import (
    ResilientOllamaClient,
    TokenEfficientClient,
)


__all__ = [
    "CODE_SPECIALIST",
    "NOVEL_SPECIALIST",
    "REASONING_SPECIALIST",
    "VALIDATED_SPECIALISTS",
    "AdaptiveRouter",
    "AdaptiveRoutingDecision",
    "AgentModule",
    "BackendCapability",
    "BackendConstraints",
    "BackendRoutingDecision",
    "BackendStatus",
    "BackendType",
    "BatchItem",
    "BatchProcessor",
    "BatchResult",
    "CacheEntry",
    "CacheOptimizationConfig",
    "ComputeBackendRouter",
    "ContextPoolManager",
    # "DynamicConcurrencyGate",  # Module unavailable
    "DynamicAgentRegistry",
    "ExecutionResult",
    "KVCacheOptimizer",
    "LRUPersistentCache",
    "ModelPoolManager",
    "ModelTierPolicy",
    "MultiAgentOrchestrator",
    "MultiLayerCache",
    "MultiLayerCacheEntry",
    "PersistentCache",
    "PersistentTokenCache",
    "PoolStatus",
    "PooledModel",
    "Priority",
    "ResilientOllamaClient",
    "RoutingDecision",
    "RoutingRequest",
    "SemanticCacheStore",
    "SpecialistAgent",
    "TierConfig",
    "TokenCacheOptimizer",
    "TokenEfficientClient",
    "ToolRegistry",
    "execute_task",
    # "get_concurrency_gate",  # Module unavailable
    "get_global_registry",
    "get_orchestrator",
    "get_persistent_cache",
    "get_pool_manager",
    "get_specialist",
    "get_token_cache_optimizer",
    "list_validated_specialists",
    "quick_orchestrate",
    "reset_pool_manager",
    "route_compute",
    "route_task",
]

# ---------------------------------------------------------------------------
# Wiring-sweep 2026-06-22: guarded re-exports for import-graph orphan modules
# All blocks use contextlib.suppress(Exception) so heavy/broken deps don't
# break the package import. Names that collide with existing exports are given
# unique module-scoped aliases; ruff-safe "as X as X" pattern used throughout.
# ---------------------------------------------------------------------------

# Wiring-sweep 2026-06-22: agent_factory.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.agent_factory import AgentConfig as AgentConfig
    from cohezion.swarm.agent_factory import AgentFactory as AgentFactory

# Wiring-sweep 2026-06-22: anomaly_detector.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.anomaly_detector import AnomalyDetector as AnomalyDetector
    from cohezion.swarm.anomaly_detector import AnomalyType as AnomalyType
    from cohezion.swarm.anomaly_detector import get_anomaly_detector as get_anomaly_detector

# Wiring-sweep 2026-06-22: auto_improving_parser.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.auto_improving_parser import AutoImprovingParser as AutoImprovingParser
    from cohezion.swarm.auto_improving_parser import PatternLearner as PatternLearner

# Wiring-sweep 2026-06-22: autoresearch_executor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.autoresearch_executor import AutoresearchExecutor as AutoresearchExecutor

# Wiring-sweep 2026-06-22: compat.py was a genuine import-graph orphan.
# SwarmOrchestrator name is unique here (compat legacy shim).
with contextlib.suppress(Exception):
    from cohezion.swarm.compat import AgentCapability as AgentCapability
    from cohezion.swarm.compat import SwarmOrchestrator as SwarmOrchestrator

# Wiring-sweep 2026-06-22: compound_client.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.compound_client import create_compound_client as create_compound_client
    from cohezion.swarm.compound_client import get_compound_client as get_compound_client
    from cohezion.swarm.compound_client import reset_compound_client as reset_compound_client

# Wiring-sweep 2026-06-22: context_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.context_model_router import ModelContextProfile as ModelContextProfile

# Wiring-sweep 2026-06-22: cost_aware_router.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.cost_aware_router import CostAwareRouter as CostAwareRouter
    from cohezion.swarm.cost_aware_router import QueryComplexity as QueryComplexity
    from cohezion.swarm.cost_aware_router import get_cost_aware_router as get_cost_aware_router

# Wiring-sweep 2026-06-22: democratic_debate.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.democratic_debate import DebateSession as DebateSession
    from cohezion.swarm.democratic_debate import DemocraticDebate as DemocraticDebate

# Wiring-sweep 2026-06-22: deterministic_discovery_with_skill_fallback.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        BalancedModelDiscovery as BalancedModelDiscovery,
    )
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        DeterministicDiscovery as DeterministicDiscovery,
    )

# Wiring-sweep 2026-06-22: dynamic_concurrency_gate.py was a genuine import-graph orphan.
# (Previously commented out as unavailable; suppress handles failure gracefully.)
with contextlib.suppress(Exception):
    from cohezion.swarm.dynamic_concurrency_gate import (
        DynamicConcurrencyGate as DynamicConcurrencyGate,
    )
    from cohezion.swarm.dynamic_concurrency_gate import get_concurrency_gate as get_concurrency_gate

# Wiring-sweep 2026-06-22: dynamic_levers.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.dynamic_levers import DynamicLever as DynamicLever
    from cohezion.swarm.dynamic_levers import DynamicLeverSystem as DynamicLeverSystem

# Wiring-sweep 2026-06-22: dynamic_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.dynamic_model_router import DynamicModelRouter as DynamicModelRouter

# Wiring-sweep 2026-06-22: execution_orchestrator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator as ExecutionOrchestrator
    from cohezion.swarm.execution_orchestrator import ExecutionReport as ExecutionReport

# Wiring-sweep 2026-06-22: fallback_strategy.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.fallback_strategy import FallbackStrategy as FallbackStrategy
    from cohezion.swarm.fallback_strategy import get_fallback_strategy as get_fallback_strategy

# Wiring-sweep 2026-06-22: gemma4_router.py was a genuine import-graph orphan.
# RoutingDecision already exported from hardware_aware_router; use unique alias.
with contextlib.suppress(Exception):
    from cohezion.swarm.gemma4_router import Gemma4Router as Gemma4Router
    from cohezion.swarm.gemma4_router import RoutingDecision as Gemma4RoutingDecision  # noqa: F401

# Wiring-sweep 2026-06-22: hf_modelfile_builder.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.hf_modelfile_builder import HFModelfileBuilder as HFModelfileBuilder

# Wiring-sweep 2026-06-22: hiho_vector_engine.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.hiho_vector_engine import HihoVectorEngine as HihoVectorEngine

# Wiring-sweep 2026-06-22: improved_deterministic_parser.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.improved_deterministic_parser import ImprovedFLMParser as ImprovedFLMParser

# Wiring-sweep 2026-06-22: intelligence_pipeline.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.intelligence_pipeline import (
        MixtureOfExpertsRouter as MixtureOfExpertsRouter,
    )

# Wiring-sweep 2026-06-22: journey_narrator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.journey_narrator import JourneyNarrator as JourneyNarrator

# Wiring-sweep 2026-06-22: lemonade_manager.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.lemonade_manager import LemonadeManager as LemonadeManager

# Wiring-sweep 2026-06-22: lemonade_model_enhancer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.lemonade_model_enhancer import (
        LemonadeModelEnhancer as LemonadeModelEnhancer,
    )

# Wiring-sweep 2026-06-22: lru_persistent_token_cache.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.lru_persistent_token_cache import (
        LRUPersistentTokenCache as LRUPersistentTokenCache,
    )

# Wiring-sweep 2026-06-22: meta_learner.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.meta_learner import MetaLearner as MetaLearner

# Wiring-sweep 2026-06-22: mitosis_apoptosis.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.mitosis_apoptosis import SwarmGovernor as SwarmGovernor

# Wiring-sweep 2026-06-22: mode_controller.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.mode_controller import ModeController as ModeController
    from cohezion.swarm.mode_controller import get_mode_controller as get_mode_controller

# Wiring-sweep 2026-06-22: model_adapter.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_adapter import SmartRouterAdapter as SmartRouterAdapter

# Wiring-sweep 2026-06-22: model_capability_registry.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_capability_registry import (
        ModelCapabilityRegistry as ModelCapabilityRegistry,
    )

# Wiring-sweep 2026-06-22: model_capability_registry_resource_safe.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_capability_registry_resource_safe import (
        ResourceSafeModelCapabilityRegistry as ResourceSafeModelCapabilityRegistry,
    )

# Wiring-sweep 2026-06-22: model_fallback_strategy.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_fallback_strategy import (
        ModelFallbackStrategy as ModelFallbackStrategy,
    )

# Wiring-sweep 2026-06-22: model_manager.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_manager import OllamaModelManager as OllamaModelManager

# Wiring-sweep 2026-06-22: model_ranker.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.model_ranker import ModelRanker as ModelRanker
    from cohezion.swarm.model_ranker import RankingStrategy as RankingStrategy

# Wiring-sweep 2026-06-22: ollama_context_manager.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.ollama_context_manager import OllamaContextManager as OllamaContextManager

# Wiring-sweep 2026-06-22: ollama_resilience.py was a genuine import-graph orphan.
# ResilientOllamaClient already exported from token_client; use unique alias.
with contextlib.suppress(Exception):
    from cohezion.swarm.ollama_resilience import (
        ResilientOllamaClient as OllamaResilientClient,  # noqa: F401
    )

# Wiring-sweep 2026-06-22: orchestrator.py was a genuine import-graph orphan.
# SwarmConfig collides with swarm_types.SwarmConfig; use unique alias.
with contextlib.suppress(Exception):
    from cohezion.swarm.orchestrator import SimpleSwarm as SimpleSwarm
    from cohezion.swarm.orchestrator import Swarm as Swarm
    from cohezion.swarm.orchestrator import SwarmConfig as OrchestratorSwarmConfig  # noqa: F401

# Wiring-sweep 2026-06-22: parser_v3_validation_oracle.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.parser_v3_validation_oracle import ParserV3 as ParserV3
    from cohezion.swarm.parser_v3_validation_oracle import ValidationOracle as ValidationOracle

# Wiring-sweep 2026-06-22: plasma_swarm_router.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.plasma_swarm_router import PlasmaSwarmRouter as PlasmaSwarmRouter

# Wiring-sweep 2026-06-22: predictive_lever_adjuster.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.predictive_lever_adjuster import (
        PredictiveLeverAdjuster as PredictiveLeverAdjuster,
    )

# Wiring-sweep 2026-06-22: quadrature_nexus.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.quadrature_nexus import QuadratureNexus as QuadratureNexus
    from cohezion.swarm.quadrature_nexus import QuadratureResult as QuadratureResult

# Wiring-sweep 2026-06-22: redundancy_suppression.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.redundancy_suppression import RedundancyManager as RedundancyManager

# Wiring-sweep 2026-06-22: research_orchestrator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.research_orchestrator import ResearchFinding as ResearchFinding
    from cohezion.swarm.research_orchestrator import ResearchOrchestrator as ResearchOrchestrator

# Wiring-sweep 2026-06-22: resonance.py was a genuine import-graph orphan.
# SwarmOrchestrator already wired from compat; use unique alias for resonance variant.
with contextlib.suppress(Exception):
    from cohezion.swarm.resonance import ResonanceProtocol as ResonanceProtocol
    from cohezion.swarm.resonance import ResonanceState as ResonanceState
    from cohezion.swarm.resonance import (
        SwarmOrchestrator as ResonanceSwarmOrchestrator,  # noqa: F401
    )

# Wiring-sweep 2026-06-22: routing_orchestrator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.routing_orchestrator import RoutingOrchestrator as RoutingOrchestrator
    from cohezion.swarm.routing_orchestrator import UnifiedRoutingDecision as UnifiedRoutingDecision

# Wiring-sweep 2026-06-22: r_zero_evolver.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.r_zero_evolver import RZeroEvolver as RZeroEvolver

# Wiring-sweep 2026-06-22: semantic_cache.py was a genuine import-graph orphan.
# (Different from cache/semantic_cache.py — this is the swarm-local implementation.)
with contextlib.suppress(Exception):
    from cohezion.swarm.semantic_cache import EmbeddingResult as EmbeddingResult
    from cohezion.swarm.semantic_cache import SemanticCache as SwarmSemanticCache  # noqa: F401
    from cohezion.swarm.semantic_cache import SemanticCacheHit as SemanticCacheHit

# Wiring-sweep 2026-06-22: smart_router.py was a genuine import-graph orphan.
# RoutingDecision collides with hardware_aware_router; use unique alias.
with contextlib.suppress(Exception):
    from cohezion.swarm.smart_router import RoutingDecision as SmartRoutingDecision  # noqa: F401
    from cohezion.swarm.smart_router import SmartRouter as SmartRouter

# Wiring-sweep 2026-06-22: swarm_types.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.swarm_types import Perspective as Perspective
    from cohezion.swarm.swarm_types import SwarmConfig as SwarmConfig
    from cohezion.swarm.swarm_types import ThoughtVector as ThoughtVector

# Wiring-sweep 2026-06-22: team_execution.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.team_execution import TeamCompoundExecutor as TeamCompoundExecutor

# Wiring-sweep 2026-06-22: team_metrics.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.team_metrics import TeamCompoundMetrics as TeamCompoundMetrics
    from cohezion.swarm.team_metrics import TeamMetricsAggregator as TeamMetricsAggregator

# Wiring-sweep 2026-06-22: team_orchestrator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.team_orchestrator import TeamOrchestrator as TeamOrchestrator
    from cohezion.swarm.team_orchestrator import TeamPlan as TeamPlan

# Wiring-sweep 2026-06-22: tip_of_spear_router.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter as TipOfTheSpearRouter

# Wiring-sweep 2026-06-22: topological_router.py was a genuine import-graph orphan.
# RoutingDecision collides with hardware_aware_router; use unique alias.
with contextlib.suppress(Exception):
    from cohezion.swarm.topological_router import (
        RoutingDecision as TopologicalRoutingDecision,  # noqa: F401
    )
    from cohezion.swarm.topological_router import TopologicalRouter as TopologicalRouter

# Wiring-sweep 2026-06-22: triune_consensus.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.triune_consensus import ConsensusReport as ConsensusReport
    from cohezion.swarm.triune_consensus import TriuneConsensus as TriuneConsensus

# Wiring-sweep 2026-06-22: triune_integration.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.triune_integration import TriuneAGI as TriuneAGI
    from cohezion.swarm.triune_integration import TriuneState as TriuneState

# Wiring-sweep 2026-06-22: unified_thinker.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.unified_thinker import UnifiedThinker as UnifiedThinker

# Wiring-sweep 2026-06-22: vmodel_engineering.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.vmodel_engineering import (
        VModelEngineeringProcess as VModelEngineeringProcess,
    )
    from cohezion.swarm.vmodel_engineering import VPhase as VPhase

# Wiring-sweep 2026-06-22: vmodel_phase_optimizer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.swarm.vmodel_phase_optimizer import (
        InstrumentedVModelEngineering as InstrumentedVModelEngineering,
    )
    from cohezion.swarm.vmodel_phase_optimizer import PhaseOptimizer as PhaseOptimizer
