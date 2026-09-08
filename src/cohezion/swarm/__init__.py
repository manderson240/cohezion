"""Swarm orchestration and token-efficient inference."""

# Note: Some imports are currently broken due to missing modules.
# They are commented out to allow the rest of the codebase to function.
# TODO: Restore these imports once the underlying modules are implemented:
# - adaptive_router_adapter
# - hardware_profiler_stub
import contextlib


try:
    from cohezion.swarm.adaptive_router import AdaptiveRouter as AdaptiveRouter
    from cohezion.swarm.adaptive_router import RoutingDecision as AdaptiveRoutingDecision
    from cohezion.swarm.adaptive_router import route_task as route_task
except ImportError:
    pass

try:
    from cohezion.swarm.batch_processor import BatchItem as BatchItem
    from cohezion.swarm.batch_processor import BatchProcessor as BatchProcessor
    from cohezion.swarm.batch_processor import BatchResult as BatchResult
    from cohezion.swarm.batch_processor import CacheEntry as CacheEntry
except ImportError:
    pass

try:
    from cohezion.swarm.compute_backend_router import BackendCapability as BackendCapability
    from cohezion.swarm.compute_backend_router import BackendConstraints as BackendConstraints
    from cohezion.swarm.compute_backend_router import BackendStatus as BackendStatus
    from cohezion.swarm.compute_backend_router import BackendType as BackendType
    from cohezion.swarm.compute_backend_router import ComputeBackendRouter as ComputeBackendRouter
    from cohezion.swarm.compute_backend_router import RoutingDecision as BackendRoutingDecision
    from cohezion.swarm.compute_backend_router import route_compute as route_compute
except ImportError:
    pass

# Wiring-sweep re-exports, table-driven (elegant-simplicity audit 2026-08-14).
# Same runtime surface and silent-suppress semantics as the former per-module
# try-blocks: each (name, alias) lands in module globals iff its module imports.
_OPTIONAL_EXPORTS: dict[str, list[tuple[str, str]]] = {
    "dynamic_agent_registry": [
        ("AgentModule", "AgentModule"),
        ("DynamicAgentRegistry", "DynamicAgentRegistry"),
        ("get_global_registry", "get_global_registry"),
    ],
    "model_pool_config": [
        ("ModelTierPolicy", "ModelTierPolicy"),
        ("PooledModel", "PooledModel"),
        ("PoolStatus", "PoolStatus"),
        ("TierConfig", "TierConfig"),
    ],
    "model_pool_manager": [
        ("ModelPoolManager", "ModelPoolManager"),
        ("get_pool_manager", "get_pool_manager"),
        ("reset_pool_manager", "reset_pool_manager"),
    ],
    "multi_layer_cache": [
        ("CacheEntry", "MultiLayerCacheEntry"),
        ("ContextPoolManager", "ContextPoolManager"),
        ("KVCacheOptimizer", "KVCacheOptimizer"),
        ("MultiLayerCache", "MultiLayerCache"),
        ("SemanticCacheStore", "SemanticCacheStore"),
    ],
    "persistent_cache": [
        ("PersistentCache", "PersistentCache"),
        ("get_persistent_cache", "get_persistent_cache"),
    ],
    "agent_factory": [
        ("AgentConfig", "AgentConfig"),
        ("AgentFactory", "AgentFactory"),
    ],
    "anomaly_detector": [
        ("AnomalyDetector", "AnomalyDetector"),
        ("AnomalyType", "AnomalyType"),
        ("get_anomaly_detector", "get_anomaly_detector"),
    ],
    "auto_improving_parser": [
        ("AutoImprovingParser", "AutoImprovingParser"),
        ("PatternLearner", "PatternLearner"),
    ],
    "compat": [
        ("AgentCapability", "AgentCapability"),
        ("SwarmOrchestrator", "SwarmOrchestrator"),
    ],
    "compound_client": [
        ("create_compound_client", "create_compound_client"),
        ("get_compound_client", "get_compound_client"),
        ("reset_compound_client", "reset_compound_client"),
    ],
    "cost_aware_router": [
        ("CostAwareRouter", "CostAwareRouter"),
        ("QueryComplexity", "QueryComplexity"),
        ("get_cost_aware_router", "get_cost_aware_router"),
    ],
    "democratic_debate": [
        ("DebateSession", "DebateSession"),
        ("DemocraticDebate", "DemocraticDebate"),
    ],
    "dynamic_levers": [
        ("DynamicLever", "DynamicLever"),
        ("DynamicLeverSystem", "DynamicLeverSystem"),
    ],
    "execution_orchestrator": [
        ("ExecutionOrchestrator", "ExecutionOrchestrator"),
        ("ExecutionReport", "ExecutionReport"),
    ],
    "fallback_strategy": [
        ("FallbackStrategy", "FallbackStrategy"),
        ("get_fallback_strategy", "get_fallback_strategy"),
    ],
    "mode_controller": [
        ("ModeController", "ModeController"),
        ("get_mode_controller", "get_mode_controller"),
    ],
    "model_ranker": [
        ("ModelRanker", "ModelRanker"),
        ("RankingStrategy", "RankingStrategy"),
    ],
    "orchestrator": [
        ("SimpleSwarm", "SimpleSwarm"),
        ("Swarm", "Swarm"),
        ("SwarmConfig", "OrchestratorSwarmConfig"),
    ],
    "parser_v3_validation_oracle": [
        ("ParserV3", "ParserV3"),
        ("ValidationOracle", "ValidationOracle"),
    ],
    "quadrature_nexus": [
        ("QuadratureNexus", "QuadratureNexus"),
        ("QuadratureResult", "QuadratureResult"),
    ],
    "research_orchestrator": [
        ("ResearchFinding", "ResearchFinding"),
        ("ResearchOrchestrator", "ResearchOrchestrator"),
    ],
    "routing_orchestrator": [
        ("RoutingOrchestrator", "RoutingOrchestrator"),
        ("UnifiedRoutingDecision", "UnifiedRoutingDecision"),
    ],
    "semantic_cache": [
        ("EmbeddingResult", "EmbeddingResult"),
        ("SemanticCache", "SwarmSemanticCache"),
        ("SemanticCacheHit", "SemanticCacheHit"),
    ],
    "swarm_types": [
        ("Perspective", "Perspective"),
        ("SwarmConfig", "SwarmConfig"),
        ("ThoughtVector", "ThoughtVector"),
    ],
    "team_metrics": [
        ("TeamCompoundMetrics", "TeamCompoundMetrics"),
        ("TeamMetricsAggregator", "TeamMetricsAggregator"),
    ],
    "team_orchestrator": [
        ("TeamOrchestrator", "TeamOrchestrator"),
        ("TeamPlan", "TeamPlan"),
    ],
    "triune_consensus": [
        ("ConsensusReport", "ConsensusReport"),
        ("TriuneConsensus", "TriuneConsensus"),
    ],
    "triune_integration": [
        ("TriuneAGI", "TriuneAGI"),
        ("TriuneState", "TriuneState"),
    ],
}


def _load_optional_exports() -> None:
    import importlib

    for _mod, _names in _OPTIONAL_EXPORTS.items():
        try:
            _m = importlib.import_module(f"cohezion.swarm.{_mod}")
        except ImportError:
            continue
        for _name, _alias in _names:
            with contextlib.suppress(AttributeError):
                globals()[_alias] = getattr(_m, _name)


_load_optional_exports()

try:
    from cohezion.swarm.hardware_aware_router import Priority as Priority
    from cohezion.swarm.hardware_aware_router import RoutingDecision as RoutingDecision
    from cohezion.swarm.hardware_aware_router import RoutingRequest as RoutingRequest
except ImportError:
    pass

with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.lru_persistent_cache import LRUPersistentCache as LRUPersistentCache

try:
    from cohezion.swarm.multi_agent_orchestrator import ExecutionResult as ExecutionResult
    from cohezion.swarm.multi_agent_orchestrator import (
        MultiAgentOrchestrator as MultiAgentOrchestrator,
    )
    from cohezion.swarm.multi_agent_orchestrator import execute_task as execute_task
    from cohezion.swarm.multi_agent_orchestrator import get_orchestrator as get_orchestrator
    from cohezion.swarm.multi_agent_orchestrator import quick_orchestrate as quick_orchestrate
except ImportError:
    pass

# from cohezion.swarm.dynamic_concurrency_gate import (
#     DynamicConcurrencyGate,
#     get_concurrency_gate,
# )
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.persistent_token_cache import PersistentTokenCache as PersistentTokenCache

# Multi-agent orchestration (dynamic + adaptive)
try:
    from cohezion.swarm.specialist_agents import CODE_SPECIALIST as CODE_SPECIALIST
    from cohezion.swarm.specialist_agents import NOVEL_SPECIALIST as NOVEL_SPECIALIST
    from cohezion.swarm.specialist_agents import REASONING_SPECIALIST as REASONING_SPECIALIST
    from cohezion.swarm.specialist_agents import VALIDATED_SPECIALISTS as VALIDATED_SPECIALISTS
    from cohezion.swarm.specialist_agents import SpecialistAgent as SpecialistAgent
    from cohezion.swarm.specialist_agents import ToolRegistry as ToolRegistry
    from cohezion.swarm.specialist_agents import get_specialist as get_specialist
    from cohezion.swarm.specialist_agents import (
        list_validated_specialists as list_validated_specialists,
    )
except ImportError:
    pass

try:
    from cohezion.swarm.token_cache_optimizer import (
        CacheOptimizationConfig as CacheOptimizationConfig,
    )
    from cohezion.swarm.token_cache_optimizer import TokenCacheOptimizer as TokenCacheOptimizer
    from cohezion.swarm.token_cache_optimizer import (
        get_token_cache_optimizer as get_token_cache_optimizer,
    )
except ImportError:
    pass

try:
    from cohezion.swarm.token_client import ResilientOllamaClient as ResilientOllamaClient
    from cohezion.swarm.token_client import TokenEfficientClient as TokenEfficientClient
except ImportError:
    pass


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
    # Wiring-sweep 2026-06-22 renamed re-exports (A as B aliases need __all__ for Pyright)
    "Gemma4RoutingDecision",
    "KVCacheOptimizer",
    "LRUPersistentCache",
    "ModelPoolManager",
    "ModelTierPolicy",
    "MultiAgentOrchestrator",
    "MultiLayerCache",
    "MultiLayerCacheEntry",
    "OllamaResilientClient",
    "OrchestratorSwarmConfig",
    "PersistentCache",
    "PersistentTokenCache",
    "PoolStatus",
    "PooledModel",
    "Priority",
    "ResilientOllamaClient",
    "ResonanceSwarmOrchestrator",
    "RoutingDecision",
    "RoutingRequest",
    "SemanticCacheStore",
    "SmartRoutingDecision",
    "SpecialistAgent",
    "SwarmSemanticCache",
    "TierConfig",
    "TokenCacheOptimizer",
    "TokenEfficientClient",
    "ToolRegistry",
    "TopologicalRoutingDecision",
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
# All blocks use try/except (ImportError, ModuleNotFoundError) so heavy/broken deps don't
# break the package import. Names that collide with existing exports are given
# unique module-scoped aliases; ruff-safe "as X as X" pattern used throughout.
# ---------------------------------------------------------------------------

# Wiring-sweep 2026-06-22: autoresearch_executor.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.autoresearch_executor import AutoresearchExecutor as AutoresearchExecutor

# Wiring-sweep 2026-06-22: compat.py was a genuine import-graph orphan.
# Wiring-sweep 2026-06-22: context_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.context_model_router import ModelContextProfile as ModelContextProfile

# Wiring-sweep 2026-06-22: deterministic_discovery_with_skill_fallback.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        BalancedModelDiscovery as BalancedModelDiscovery,
    )
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        DeterministicDiscovery as DeterministicDiscovery,
    )
except ImportError:
    pass

# Wiring-sweep 2026-06-22: dynamic_concurrency_gate.py was a genuine import-graph orphan.
# (Previously commented out as unavailable; suppress handles failure gracefully.)
try:
    from cohezion.swarm.dynamic_concurrency_gate import (
        DynamicConcurrencyGate as DynamicConcurrencyGate,
    )
    from cohezion.swarm.dynamic_concurrency_gate import get_concurrency_gate as get_concurrency_gate
except ImportError:
    pass

# Wiring-sweep 2026-06-22: dynamic_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.dynamic_model_router import DynamicModelRouter as DynamicModelRouter

# Wiring-sweep 2026-06-22: gemma4_router.py was a genuine import-graph orphan.
# RoutingDecision already exported from hardware_aware_router; use unique alias.
try:
    from cohezion.swarm.gemma4_router import Gemma4Router as Gemma4Router
    from cohezion.swarm.gemma4_router import RoutingDecision as Gemma4RoutingDecision
except ImportError:
    pass

# Wiring-sweep 2026-06-22: hf_modelfile_builder.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.hf_modelfile_builder import HFModelfileBuilder as HFModelfileBuilder

# Wiring-sweep 2026-06-22: hiho_vector_engine.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.hiho_vector_engine import HihoVectorEngine as HihoVectorEngine

# Wiring-sweep 2026-06-22: improved_deterministic_parser.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.improved_deterministic_parser import ImprovedFLMParser as ImprovedFLMParser

# Wiring-sweep 2026-06-22: intelligence_pipeline.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.intelligence_pipeline import (
        MixtureOfExpertsRouter as MixtureOfExpertsRouter,
    )

# Wiring-sweep 2026-06-22: journey_narrator.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.journey_narrator import JourneyNarrator as JourneyNarrator

# Wiring-sweep 2026-06-22: lemonade_manager.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.lemonade_manager import LemonadeManager as LemonadeManager

# Wiring-sweep 2026-06-22: lemonade_model_enhancer.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.lemonade_model_enhancer import (
        LemonadeModelEnhancer as LemonadeModelEnhancer,
    )

# Wiring-sweep 2026-06-22: lru_persistent_token_cache.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.lru_persistent_token_cache import (
        LRUPersistentTokenCache as LRUPersistentTokenCache,
    )

# Wiring-sweep 2026-06-22: meta_learner.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.meta_learner import MetaLearner as MetaLearner

# Wiring-sweep 2026-06-22: mitosis_apoptosis.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.mitosis_apoptosis import SwarmGovernor as SwarmGovernor

# Wiring-sweep 2026-06-22: model_adapter.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.model_adapter import SmartRouterAdapter as SmartRouterAdapter

# Wiring-sweep 2026-06-22: model_capability_registry.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.model_capability_registry import (
        ModelCapabilityRegistry as ModelCapabilityRegistry,
    )

# Wiring-sweep 2026-06-22: model_capability_registry_resource_safe.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.model_capability_registry_resource_safe import (
        ResourceSafeModelCapabilityRegistry as ResourceSafeModelCapabilityRegistry,
    )

# Wiring-sweep 2026-06-22: model_fallback_strategy.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.model_fallback_strategy import (
        ModelFallbackStrategy as ModelFallbackStrategy,
    )

# Wiring-sweep 2026-06-22: model_manager.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.model_manager import OllamaModelManager as OllamaModelManager

# Wiring-sweep 2026-06-22: ollama_context_manager.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.ollama_context_manager import OllamaContextManager as OllamaContextManager

# Wiring-sweep 2026-06-22: ollama_resilience.py was a genuine import-graph orphan.
# ResilientOllamaClient already exported from token_client; use unique alias.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.ollama_resilience import (
        ResilientOllamaClient as OllamaResilientClient,
    )

# Wiring-sweep 2026-06-22: orchestrator.py was a genuine import-graph orphan.
# Wiring-sweep 2026-06-22: plasma_swarm_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.plasma_swarm_router import PlasmaSwarmRouter as PlasmaSwarmRouter

# Wiring-sweep 2026-06-22: predictive_lever_adjuster.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.predictive_lever_adjuster import (
        PredictiveLeverAdjuster as PredictiveLeverAdjuster,
    )

# Wiring-sweep 2026-06-22: redundancy_suppression.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.redundancy_suppression import RedundancyManager as RedundancyManager

# Wiring-sweep 2026-06-22: resonance.py was a genuine import-graph orphan.
# SwarmOrchestrator already wired from compat; use unique alias for resonance variant.
try:
    from cohezion.swarm.resonance import ResonanceProtocol as ResonanceProtocol
    from cohezion.swarm.resonance import ResonanceState as ResonanceState
    from cohezion.swarm.resonance import (
        SwarmOrchestrator as ResonanceSwarmOrchestrator,
    )
except ImportError:
    pass

# Wiring-sweep 2026-06-22: r_zero_evolver.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.r_zero_evolver import RZeroEvolver as RZeroEvolver

# Wiring-sweep 2026-06-22: semantic_cache.py was a genuine import-graph orphan.
# Wiring-sweep 2026-06-22: smart_router.py was a genuine import-graph orphan.
# RoutingDecision collides with hardware_aware_router; use unique alias.
try:
    from cohezion.swarm.smart_router import RoutingDecision as SmartRoutingDecision
    from cohezion.swarm.smart_router import SmartRouter as SmartRouter
except ImportError:
    pass

# Wiring-sweep 2026-06-22: team_execution.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.team_execution import TeamCompoundExecutor as TeamCompoundExecutor

# Wiring-sweep 2026-06-22: tip_of_spear_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter as TipOfTheSpearRouter

# Wiring-sweep 2026-06-22: topological_router.py was a genuine import-graph orphan.
# RoutingDecision collides with hardware_aware_router; use unique alias.
try:
    from cohezion.swarm.topological_router import (
        RoutingDecision as TopologicalRoutingDecision,
    )
    from cohezion.swarm.topological_router import TopologicalRouter as TopologicalRouter
except ImportError:
    pass

# Wiring-sweep 2026-06-22: unified_thinker.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.unified_thinker import UnifiedThinker as UnifiedThinker

# Wiring-sweep 2026-06-22: vmodel_engineering.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.vmodel_engineering import (
        VModelEngineeringProcess as VModelEngineeringProcess,
    )
    from cohezion.swarm.vmodel_engineering import VPhase as VPhase
except ImportError:
    pass

# Wiring-sweep 2026-06-22: vmodel_phase_optimizer.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.vmodel_phase_optimizer import (
        InstrumentedVModelEngineering as InstrumentedVModelEngineering,
    )
    from cohezion.swarm.vmodel_phase_optimizer import PhaseOptimizer as PhaseOptimizer
except ImportError:
    pass
