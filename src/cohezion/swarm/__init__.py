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
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.batch_processor import BatchItem as BatchItem
    from cohezion.swarm.batch_processor import BatchProcessor as BatchProcessor
    from cohezion.swarm.batch_processor import BatchResult as BatchResult
    from cohezion.swarm.batch_processor import CacheEntry as CacheEntry
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.compute_backend_router import BackendCapability as BackendCapability
    from cohezion.swarm.compute_backend_router import BackendConstraints as BackendConstraints
    from cohezion.swarm.compute_backend_router import BackendStatus as BackendStatus
    from cohezion.swarm.compute_backend_router import BackendType as BackendType
    from cohezion.swarm.compute_backend_router import ComputeBackendRouter as ComputeBackendRouter
    from cohezion.swarm.compute_backend_router import RoutingDecision as BackendRoutingDecision
    from cohezion.swarm.compute_backend_router import route_compute as route_compute
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.dynamic_agent_registry import AgentModule as AgentModule
    from cohezion.swarm.dynamic_agent_registry import DynamicAgentRegistry as DynamicAgentRegistry
    from cohezion.swarm.dynamic_agent_registry import get_global_registry as get_global_registry
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.hardware_aware_router import Priority as Priority
    from cohezion.swarm.hardware_aware_router import RoutingDecision as RoutingDecision
    from cohezion.swarm.hardware_aware_router import RoutingRequest as RoutingRequest
except (ImportError, ModuleNotFoundError):
    pass

with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.lru_persistent_cache import LRUPersistentCache as LRUPersistentCache

try:
    from cohezion.swarm.model_pool_config import ModelTierPolicy as ModelTierPolicy
    from cohezion.swarm.model_pool_config import PooledModel as PooledModel
    from cohezion.swarm.model_pool_config import PoolStatus as PoolStatus
    from cohezion.swarm.model_pool_config import TierConfig as TierConfig
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.model_pool_manager import ModelPoolManager as ModelPoolManager
    from cohezion.swarm.model_pool_manager import get_pool_manager as get_pool_manager
    from cohezion.swarm.model_pool_manager import reset_pool_manager as reset_pool_manager
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.multi_agent_orchestrator import ExecutionResult as ExecutionResult
    from cohezion.swarm.multi_agent_orchestrator import (
        MultiAgentOrchestrator as MultiAgentOrchestrator,
    )
    from cohezion.swarm.multi_agent_orchestrator import execute_task as execute_task
    from cohezion.swarm.multi_agent_orchestrator import get_orchestrator as get_orchestrator
    from cohezion.swarm.multi_agent_orchestrator import quick_orchestrate as quick_orchestrate
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.multi_layer_cache import CacheEntry as MultiLayerCacheEntry
    from cohezion.swarm.multi_layer_cache import ContextPoolManager as ContextPoolManager
    from cohezion.swarm.multi_layer_cache import KVCacheOptimizer as KVCacheOptimizer
    from cohezion.swarm.multi_layer_cache import MultiLayerCache as MultiLayerCache
    from cohezion.swarm.multi_layer_cache import SemanticCacheStore as SemanticCacheStore
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.persistent_cache import PersistentCache as PersistentCache
    from cohezion.swarm.persistent_cache import get_persistent_cache as get_persistent_cache
except (ImportError, ModuleNotFoundError):
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
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.token_cache_optimizer import (
        CacheOptimizationConfig as CacheOptimizationConfig,
    )
    from cohezion.swarm.token_cache_optimizer import TokenCacheOptimizer as TokenCacheOptimizer
    from cohezion.swarm.token_cache_optimizer import (
        get_token_cache_optimizer as get_token_cache_optimizer,
    )
except (ImportError, ModuleNotFoundError):
    pass

try:
    from cohezion.swarm.token_client import ResilientOllamaClient as ResilientOllamaClient
    from cohezion.swarm.token_client import TokenEfficientClient as TokenEfficientClient
except (ImportError, ModuleNotFoundError):
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

# Wiring-sweep 2026-06-22: agent_factory.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.agent_factory import AgentConfig as AgentConfig
    from cohezion.swarm.agent_factory import AgentFactory as AgentFactory
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: anomaly_detector.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.anomaly_detector import AnomalyDetector as AnomalyDetector
    from cohezion.swarm.anomaly_detector import AnomalyType as AnomalyType
    from cohezion.swarm.anomaly_detector import get_anomaly_detector as get_anomaly_detector
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: auto_improving_parser.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.auto_improving_parser import AutoImprovingParser as AutoImprovingParser
    from cohezion.swarm.auto_improving_parser import PatternLearner as PatternLearner
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: autoresearch_executor.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.autoresearch_executor import AutoresearchExecutor as AutoresearchExecutor

# Wiring-sweep 2026-06-22: compat.py was a genuine import-graph orphan.
# SwarmOrchestrator name is unique here (compat legacy shim).
try:
    from cohezion.swarm.compat import AgentCapability as AgentCapability
    from cohezion.swarm.compat import SwarmOrchestrator as SwarmOrchestrator
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: compound_client.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.compound_client import create_compound_client as create_compound_client
    from cohezion.swarm.compound_client import get_compound_client as get_compound_client
    from cohezion.swarm.compound_client import reset_compound_client as reset_compound_client
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: context_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.context_model_router import ModelContextProfile as ModelContextProfile

# Wiring-sweep 2026-06-22: cost_aware_router.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.cost_aware_router import CostAwareRouter as CostAwareRouter
    from cohezion.swarm.cost_aware_router import QueryComplexity as QueryComplexity
    from cohezion.swarm.cost_aware_router import get_cost_aware_router as get_cost_aware_router
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: democratic_debate.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.democratic_debate import DebateSession as DebateSession
    from cohezion.swarm.democratic_debate import DemocraticDebate as DemocraticDebate
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: deterministic_discovery_with_skill_fallback.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        BalancedModelDiscovery as BalancedModelDiscovery,
    )
    from cohezion.swarm.deterministic_discovery_with_skill_fallback import (
        DeterministicDiscovery as DeterministicDiscovery,
    )
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: dynamic_concurrency_gate.py was a genuine import-graph orphan.
# (Previously commented out as unavailable; suppress handles failure gracefully.)
try:
    from cohezion.swarm.dynamic_concurrency_gate import (
        DynamicConcurrencyGate as DynamicConcurrencyGate,
    )
    from cohezion.swarm.dynamic_concurrency_gate import get_concurrency_gate as get_concurrency_gate
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: dynamic_levers.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.dynamic_levers import DynamicLever as DynamicLever
    from cohezion.swarm.dynamic_levers import DynamicLeverSystem as DynamicLeverSystem
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: dynamic_model_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.dynamic_model_router import DynamicModelRouter as DynamicModelRouter

# Wiring-sweep 2026-06-22: execution_orchestrator.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator as ExecutionOrchestrator
    from cohezion.swarm.execution_orchestrator import ExecutionReport as ExecutionReport
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: fallback_strategy.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.fallback_strategy import FallbackStrategy as FallbackStrategy
    from cohezion.swarm.fallback_strategy import get_fallback_strategy as get_fallback_strategy
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: gemma4_router.py was a genuine import-graph orphan.
# RoutingDecision already exported from hardware_aware_router; use unique alias.
try:
    from cohezion.swarm.gemma4_router import Gemma4Router as Gemma4Router
    from cohezion.swarm.gemma4_router import RoutingDecision as Gemma4RoutingDecision
except (ImportError, ModuleNotFoundError):
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

# Wiring-sweep 2026-06-22: mode_controller.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.mode_controller import ModeController as ModeController
    from cohezion.swarm.mode_controller import get_mode_controller as get_mode_controller
except (ImportError, ModuleNotFoundError):
    pass

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

# Wiring-sweep 2026-06-22: model_ranker.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.model_ranker import ModelRanker as ModelRanker
    from cohezion.swarm.model_ranker import RankingStrategy as RankingStrategy
except (ImportError, ModuleNotFoundError):
    pass

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
# SwarmConfig collides with swarm_types.SwarmConfig; use unique alias.
try:
    from cohezion.swarm.orchestrator import SimpleSwarm as SimpleSwarm
    from cohezion.swarm.orchestrator import Swarm as Swarm
    from cohezion.swarm.orchestrator import SwarmConfig as OrchestratorSwarmConfig
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: parser_v3_validation_oracle.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.parser_v3_validation_oracle import ParserV3 as ParserV3
    from cohezion.swarm.parser_v3_validation_oracle import ValidationOracle as ValidationOracle
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: plasma_swarm_router.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.plasma_swarm_router import PlasmaSwarmRouter as PlasmaSwarmRouter

# Wiring-sweep 2026-06-22: predictive_lever_adjuster.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.predictive_lever_adjuster import (
        PredictiveLeverAdjuster as PredictiveLeverAdjuster,
    )

# Wiring-sweep 2026-06-22: quadrature_nexus.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.quadrature_nexus import QuadratureNexus as QuadratureNexus
    from cohezion.swarm.quadrature_nexus import QuadratureResult as QuadratureResult
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: redundancy_suppression.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.redundancy_suppression import RedundancyManager as RedundancyManager

# Wiring-sweep 2026-06-22: research_orchestrator.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.research_orchestrator import ResearchFinding as ResearchFinding
    from cohezion.swarm.research_orchestrator import ResearchOrchestrator as ResearchOrchestrator
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: resonance.py was a genuine import-graph orphan.
# SwarmOrchestrator already wired from compat; use unique alias for resonance variant.
try:
    from cohezion.swarm.resonance import ResonanceProtocol as ResonanceProtocol
    from cohezion.swarm.resonance import ResonanceState as ResonanceState
    from cohezion.swarm.resonance import (
        SwarmOrchestrator as ResonanceSwarmOrchestrator,
    )
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: routing_orchestrator.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.routing_orchestrator import RoutingOrchestrator as RoutingOrchestrator
    from cohezion.swarm.routing_orchestrator import UnifiedRoutingDecision as UnifiedRoutingDecision
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: r_zero_evolver.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.r_zero_evolver import RZeroEvolver as RZeroEvolver

# Wiring-sweep 2026-06-22: semantic_cache.py was a genuine import-graph orphan.
# (Different from cache/semantic_cache.py — this is the swarm-local implementation.)
try:
    from cohezion.swarm.semantic_cache import EmbeddingResult as EmbeddingResult
    from cohezion.swarm.semantic_cache import SemanticCache as SwarmSemanticCache
    from cohezion.swarm.semantic_cache import SemanticCacheHit as SemanticCacheHit
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: smart_router.py was a genuine import-graph orphan.
# RoutingDecision collides with hardware_aware_router; use unique alias.
try:
    from cohezion.swarm.smart_router import RoutingDecision as SmartRoutingDecision
    from cohezion.swarm.smart_router import SmartRouter as SmartRouter
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: swarm_types.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.swarm_types import Perspective as Perspective
    from cohezion.swarm.swarm_types import SwarmConfig as SwarmConfig
    from cohezion.swarm.swarm_types import ThoughtVector as ThoughtVector
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: team_execution.py was a genuine import-graph orphan.
with contextlib.suppress(ImportError, ModuleNotFoundError):
    from cohezion.swarm.team_execution import TeamCompoundExecutor as TeamCompoundExecutor

# Wiring-sweep 2026-06-22: team_metrics.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.team_metrics import TeamCompoundMetrics as TeamCompoundMetrics
    from cohezion.swarm.team_metrics import TeamMetricsAggregator as TeamMetricsAggregator
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: team_orchestrator.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.team_orchestrator import TeamOrchestrator as TeamOrchestrator
    from cohezion.swarm.team_orchestrator import TeamPlan as TeamPlan
except (ImportError, ModuleNotFoundError):
    pass

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
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: triune_consensus.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.triune_consensus import ConsensusReport as ConsensusReport
    from cohezion.swarm.triune_consensus import TriuneConsensus as TriuneConsensus
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: triune_integration.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.triune_integration import TriuneAGI as TriuneAGI
    from cohezion.swarm.triune_integration import TriuneState as TriuneState
except (ImportError, ModuleNotFoundError):
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
except (ImportError, ModuleNotFoundError):
    pass

# Wiring-sweep 2026-06-22: vmodel_phase_optimizer.py was a genuine import-graph orphan.
try:
    from cohezion.swarm.vmodel_phase_optimizer import (
        InstrumentedVModelEngineering as InstrumentedVModelEngineering,
    )
    from cohezion.swarm.vmodel_phase_optimizer import PhaseOptimizer as PhaseOptimizer
except (ImportError, ModuleNotFoundError):
    pass
