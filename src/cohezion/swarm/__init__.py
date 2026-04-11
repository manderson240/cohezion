"""Swarm orchestration and token-efficient inference."""

# Note: Some imports are currently broken due to missing modules.
# They are commented out to allow the rest of the codebase to function.
# TODO: Restore these imports once the underlying modules are implemented:
# - adaptive_router_adapter
# - hardware_profiler_stub

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
    RoutingDecision as BackendRoutingDecision,
    route_compute,
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
from cohezion.swarm.token_cache_optimizer import (
    CacheOptimizationConfig,
    TokenCacheOptimizer,
    get_token_cache_optimizer,
)
from cohezion.swarm.token_client import (
    ResilientOllamaClient,
    TokenEfficientClient,
)

# Multi-agent orchestration (dynamic + adaptive)
from cohezion.swarm.specialist_agents import (
    CODE_SPECIALIST,
    NOVEL_SPECIALIST,
    REASONING_SPECIALIST,
    SpecialistAgent,
    ToolRegistry,
    VALIDATED_SPECIALISTS,
    get_specialist,
    list_validated_specialists,
)
from cohezion.swarm.dynamic_agent_registry import (
    AgentModule,
    DynamicAgentRegistry,
    get_global_registry,
)
from cohezion.swarm.adaptive_router import (
    AdaptiveRouter,
    RoutingDecision as AdaptiveRoutingDecision,
    route_task,
)
from cohezion.swarm.multi_agent_orchestrator import (
    ExecutionResult,
    MultiAgentOrchestrator,
    execute_task,
    get_orchestrator,
    quick_orchestrate,
)


__all__ = [
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
    "CODE_SPECIALIST",
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
    "NOVEL_SPECIALIST",
    "PersistentCache",
    "PersistentTokenCache",
    "PoolStatus",
    "PooledModel",
    "Priority",
    "REASONING_SPECIALIST",
    "ResilientOllamaClient",
    "RoutingDecision",
    "RoutingRequest",
    "SemanticCacheStore",
    "SpecialistAgent",
    "TierConfig",
    "TokenCacheOptimizer",
    "TokenEfficientClient",
    "ToolRegistry",
    "VALIDATED_SPECIALISTS",
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
    "execute_task",
]
