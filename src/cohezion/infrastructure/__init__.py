"""Infrastructure layer providing shared services for the Cohezion system.

This module implements compound engineering principles:
- CacheManager: Tiered caching (L1 Memory → L2 Semantic → L3 File)
- ConnectionPool: Database connection reuse and health monitoring
- EventBus: Decoupled pub/sub communication
- SecurityPipeline: Shared security components
- Repositories: Database abstraction layer
- TaskManager: Async task tracking and cleanup
- UnifiedRegistry: Consolidated capability discovery
- AgentComposer: Mixin-based agent construction
"""

from .cache_manager import (
    CacheBackend,
    CacheEntry,
    CacheKey,
    FileBackend,
    MemoryBackend,
    SemanticBackend,
    TieredCacheManager,
    get_cache_manager,
    reset_cache_manager,
)

from .connection_pool import (
    ConnectionPool,
    PoolConfig,
    PooledConnection,
    close_connection_pool,
    get_connection_pool,
)

from .event_bus import (
    Event,
    EventBus,
    EventFilter,
    EventHandlerGroup,
    EventType,
    get_event_bus,
    reset_event_bus,
)

from .security_pipeline import (
    ContentModerationRule,
    FilterResult,
    PIIProtectionRule,
    PromptInjectionRule,
    SecurityPipeline,
    SecurityResult,
    get_security_pipeline,
    reset_security_pipeline,
)

from .repositories import (
    AgentJourney,
    JourneyRepository,
    NodeRepository,
    RepositoryFactory,
    SurrealJourneyRepository,
    SurrealNodeRepository,
    UniverseNode,
    get_repository_factory,
)

from .task_manager import (
    TaskGroup,
    TaskInfo,
    TaskManager,
    TaskStatus,
    get_task_manager,
    reset_task_manager,
)

from .unified_registry import (
    Capability,
    RegistryPlugin,
    UnifiedRegistry,
    get_unified_registry,
    reset_unified_registry,
)

from .agent_composer import (
    AgentBehavior,
    AgentBuilder,
    CachingBehavior,
    ComposableAgent,
    EventPublishingBehavior,
    PersistenceBehavior,
    SecurityBehavior,
)

__all__ = [
    # Cache
    "CacheBackend",
    "CacheEntry",
    "CacheKey",
    "FileBackend",
    "MemoryBackend",
    "SemanticBackend",
    "TieredCacheManager",
    "get_cache_manager",
    "reset_cache_manager",
    # Connection Pool
    "ConnectionPool",
    "PoolConfig",
    "PooledConnection",
    "get_connection_pool",
    "close_connection_pool",
    # Event Bus
    "Event",
    "EventBus",
    "EventFilter",
    "EventHandlerGroup",
    "EventType",
    "get_event_bus",
    "reset_event_bus",
    # Security
    "ContentModerationRule",
    "FilterResult",
    "PIIProtectionRule",
    "PromptInjectionRule",
    "SecurityPipeline",
    "SecurityResult",
    "get_security_pipeline",
    "reset_security_pipeline",
    # Repositories
    "AgentJourney",
    "JourneyRepository",
    "NodeRepository",
    "RepositoryFactory",
    "SurrealJourneyRepository",
    "SurrealNodeRepository",
    "UniverseNode",
    "get_repository_factory",
    # Task Manager
    "TaskGroup",
    "TaskInfo",
    "TaskManager",
    "TaskStatus",
    "get_task_manager",
    "reset_task_manager",
    # Registry
    "Capability",
    "RegistryPlugin",
    "UnifiedRegistry",
    "get_unified_registry",
    "reset_unified_registry",
    # Agent Composer
    "AgentBehavior",
    "AgentBuilder",
    "CachingBehavior",
    "ComposableAgent",
    "EventPublishingBehavior",
    "PersistenceBehavior",
    "SecurityBehavior",
]
