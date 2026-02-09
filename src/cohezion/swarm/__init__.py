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
from cohezion.swarm.lru_persistent_cache import (
    LRUPersistentCache,
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
from cohezion.swarm.hardware_aware_router import (
    Priority,
    RoutingDecision,
    RoutingRequest,
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
    "BatchItem",
    "BatchProcessor",
    "BatchResult",
    "CacheEntry",
    "CacheOptimizationConfig",
    "ContextPoolManager",
    # "DynamicConcurrencyGate",  # Module unavailable
    "KVCacheOptimizer",
    "LRUPersistentCache",
    "MultiLayerCache",
    "MultiLayerCacheEntry",
    "PersistentCache",
    "PersistentTokenCache",
    "Priority",
    "ResilientOllamaClient",
    "RoutingDecision",
    "RoutingRequest",
    "SemanticCacheStore",
    "TokenCacheOptimizer",
    "TokenEfficientClient",
    # "get_concurrency_gate",  # Module unavailable
    "get_persistent_cache",
    "get_token_cache_optimizer",
]
