# TECHNICAL SPECIFICATION: Enhanced Model Pool with Vault Integration

**Version:** 1.0  
**Date:** 2026-02-21  
**Platform:** AMD Ryzen AI MAX+ 395 (128GB LPDDR5X-8000)  
**Based on:** Adversarial Review Findings  

---

## 1. SYSTEM OVERVIEW

### 1.1 Purpose

This specification defines a robust, fault-tolerant model management system that:
- Prevents memory exhaustion through graduated response
- Persists agentic journeys to vault for durability
- Optimizes token efficiency through context-aware routing
- Coordinates overload protection across all subsystems

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED OVERLOAD PROTECTOR                    │
│                    (overload_coordinator.py)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Memory    │  │   Request   │  │   Circuit    │          │ │
│  │   Monitor   │  │   Queue     │  │   Breaker    │          │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘          │ │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│              CONTEXT-AWARE MODEL ROUTER                           │
│              (context_model_router.py)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  KV Cache    │  │   Context    │  │  Model Selection     │   │
│  │  Tracker     │  │   Validator  │  │  Engine              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│              MODEL POOL MANAGER (Enhanced)                        │
│              (model_pool_manager.py - updated)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
│  │   HOT    │  │  WARM    │  │  COLD    │  │ Load           │    │
│  │  Tier    │  │  Tier    │  │  Tier    │  │ Coordinator    │    │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│              JOURNEY PERSISTENCE LAYER                            │
│              (journey_persistence.py)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │   Vault      │  │  SurrealDB   │  │   Local Cache        │    │
│  │   MCP        │  │  Client      │  │   (Hot Path)         │    │
│  └──────────────┘  └──────────────┘  └──────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. MODULE SPECIFICATIONS

### 2.1 Module: Unified Overload Protector

**File:** `src/cohezion/swarm/overload_coordinator.py`

**Purpose:** Central coordination for all overload protection systems with graduated response.

**Class:** `OverloadCoordinator`

**Key Attributes:**
```python
@dataclass
class ProtectionConfig:
    """Configuration for graduated overload protection."""

    # Memory pressure thresholds (graduated)
    pressure_normal: float = 0.65  # 65% - full performance
    pressure_warning: float = 0.75  # 75% - reduce context 25%
    pressure_elevated: float = 0.85  # 85% - evict cold, reduce 50%
    pressure_critical: float = 0.92  # 92% - emergency mode
    pressure_emergency: float = 0.95  # 95% - restart Ollama

    # Response delays (prevent thrashing)
    min_action_interval: float = 10.0  # Seconds between actions
    cooldown_period: float = 30.0  # Seconds before escalating

    # Circuit breaker coordination
    disable_circuits_above: float = 0.90  # Disable CB above this

    # Request throttling
    max_queue_depth: int = 10
    queue_timeout: float = 300.0
```

**Key Methods:**

```python
async def handle_memory_pressure(self, pressure: float) -> ProtectionAction:
    """
    Handle memory pressure with graduated response.

    Args:
        pressure: Current memory pressure (0.0 - 1.0)

    Returns:
        ProtectionAction detailing actions taken

    Response Matrix:
        0.00-0.65: Normal - No action
        0.65-0.75: Warning - Reduce context 25%, notify
        0.75-0.85: Elevated - Evict cold models, reduce 50%, start throttling
        0.85-0.92: Critical - Evict warm, reduce 75%, queue new requests
        0.92-0.95: Emergency - Restart Ollama, preserve hot models only
        0.95+:     Crash Prevention - Emergency restart with minimal config
    """
    ...


async def coordinate_with_circuit_breakers(self, pressure: float):
    """
    Adjust circuit breaker thresholds based on pressure.

    When pressure is high:
    - Increase failure tolerance for large models (memory-related fails)
    - Disable aggressive circuit opening
    - Focus on memory recovery instead
    """
    ...


async def validate_request(self, request: dict) -> ValidatedRequest:
    """
    Validate request against current system state.

    Checks:
    1. Context size vs available memory
    2. KV cache requirements
    3. Model availability
    4. Queue depth

    Raises:
        OverloadError: If request cannot be safely processed
    """
    ...
```

**Integration Points:**
- Called by: `ModelPoolManager`, `DynamicModelRouter`, `TokenClient`
- Calls: `ModelPoolManager.evict_model()`, `ContextRouter.adjust_context()`, `CircuitBreaker.adjust_threshold()`

---

### 2.2 Module: Context-Aware Model Router

**File:** `src/cohezion/swarm/context_model_router.py`

**Purpose:** Route requests to optimal model based on context requirements, not just task type.

**Class:** `ContextModelRouter`

**Key Attributes:**
```python
@dataclass
class ModelContextProfile:
    """Context-aware model profile."""

    name: str
    size_gb: float
    total_params_b: float
    native_context: int

    # Context optimization
    optimal_context_128gb: int  # Safe context for 128GB system
    min_context: int  # Absolute minimum (always safe)

    # KV cache calculation
    kv_cache_mb_per_1k: float  # MB of KV cache per 1K tokens
    max_kv_cache_gb: float  # Maximum KV cache to allocate

    # Performance
    tokens_per_second: float
    quality_score: float  # 0-1

    # Task suitability
    best_for: list[str]  # ["coding", "analysis", "reasoning"]
    min_context_for_quality: int  # Below this, quality degrades


# Pre-calculated profiles for 128GB system
MODEL_PROFILES = {
    "phi4-mini-reasoning:latest": ModelContextProfile(
        name="phi4-mini-reasoning:latest",
        size_gb=3.2,
        total_params_b=3.8,
        native_context=131072,
        optimal_context_128gb=131072,  # Can use full context
        min_context=4096,
        kv_cache_mb_per_1k=0.3,
        max_kv_cache_gb=40.0,
        tokens_per_second=45.0,
        quality_score=0.75,
        best_for=["reasoning", "analysis", "quick_tasks"],
        min_context_for_quality=2048,
    ),
    "qwen3-coder-next:q4_K_M": ModelContextProfile(
        name="qwen3-coder-next:q4_K_M",
        size_gb=52.0,
        total_params_b=80.0,  # 80B total, 3B active (MoE)
        native_context=262144,
        optimal_context_128gb=65536,  # Conservative for 128GB
        min_context=8192,
        kv_cache_mb_per_1k=0.8,  # MoE has different cache pattern
        max_kv_cache_gb=52.0,  # 50% of model size
        tokens_per_second=18.0,
        quality_score=0.95,
        best_for=["coding", "complex_reasoning", "large_context"],
        min_context_for_quality=8192,
    ),
    "glm-4.7-flash:latest": ModelContextProfile(
        name="glm-4.7-flash:latest",
        size_gb=19.0,
        total_params_b=30.0,  # 30B-A3B MoE
        native_context=198000,
        optimal_context_128gb=65536,
        min_context=4096,
        kv_cache_mb_per_1k=0.5,
        max_kv_cache_gb=32.0,
        tokens_per_second=25.0,
        quality_score=0.88,
        best_for=["general", "fast_response", "medium_context"],
        min_context_for_quality=4096,
    ),
}
```

**Key Methods:**

```python
async def route(self, request: RoutingRequest) -> RoutingDecision:
    """
    Route request based on context needs and system state.

    Selection Criteria (in order):
    1. Context fit: model.optimal_context >= request.context_length
    2. Memory fit: model.size + kv_cache <= available_memory * 0.8
    3. Task suitability: request.task_type in model.best_for
    4. Quality: model.quality_score >= request.min_quality
    5. Speed: model.tokens_per_second >= request.min_speed

    Fallback Strategy:
    - If no model fits context: Use largest available, truncate request
    - If no model fits memory: Queue request, evict lower priority models
    - If queue full: Reject with retry-after header
    """
    ...


def calculate_safe_context(
    self, model: ModelContextProfile, available_memory_gb: float, concurrent_requests: int = 1
) -> int:
    """
    Calculate safe context window for model.

    Formula:
        usable_memory = available_memory_gb * 0.75 - 5  # 75% minus 5GB system
        kv_budget_per_request = (usable_memory * 1024) / concurrent_requests
        max_context_from_kv = (kv_budget_per_request / model.kv_cache_mb_per_1k) * 1000
        safe_context = min(max_context_from_kv, model.optimal_context_128gb, model.native_context)
        return max(safe_context, model.min_context)
    """
    ...


def get_context_efficiency_score(self, model: ModelContextProfile, requested_context: int) -> float:
    """
    Calculate token efficiency for this model-context combination.

    Efficiency = (useful_tokens / total_tokens) * quality_factor

    Example:
    - 2K request on 256K model: 0.008 * 0.95 = 0.76% efficiency (BAD)
    - 64K request on 256K model: 0.25 * 0.95 = 23.75% efficiency (GOOD)
    - 2K request on 4K model: 0.5 * 0.75 = 37.5% efficiency (GOOD)
    """
    ...
```

**Integration Points:**
- Called by: `CompoundExecutor`, `SmartRouter`
- Calls: `OverloadCoordinator.validate_request()`, `ModelPoolManager.ensure_loaded()`, `KVCacheTracker.allocate()`

---

### 2.3 Module: KV Cache Tracker

**File:** `src/cohezion/swarm/kv_cache_tracker.py`

**Purpose:** Track and manage KV cache memory across all active requests.

**Class:** `KVCacheTracker`

**Key Attributes:**
```python
@dataclass
class KVCacheEntry:
    """Tracks KV cache for a single request."""

    request_id: str
    model: str
    context_length: int
    kv_cache_mb: float
    created_at: datetime
    last_accessed: datetime

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def idle_seconds(self) -> float:
        return (datetime.now() - self.last_accessed).total_seconds()


class KVCacheTracker:
    def __init__(self, max_total_cache_gb: float = 60.0):
        self.active_caches: dict[str, KVCacheEntry] = {}  # request_id -> entry
        self.max_total_cache_gb = max_total_cache_gb  # 60GB for 128GB system
        self._lock = asyncio.Lock()
```

**Key Methods:**

```python
async def allocate(
    self, request_id: str, model: ModelContextProfile, context_length: int, timeout: float = 5.0
) -> AllocationResult:
    """
    Allocate KV cache for a request.

    Algorithm:
    1. Calculate required KV cache: context_length/1000 * model.kv_cache_mb_per_1k
    2. Check if under max_total_cache_gb
    3. If over: evict oldest idle caches
    4. If still over: reduce context length
    5. If still over: queue request

    Returns:
        AllocationResult with:
        - success: bool
        - allocated_context: int (may be reduced)
        - kv_cache_mb: float
        - queue_position: int (0 if immediate)
    """
    ...


async def release(self, request_id: str) -> float:
    """
    Release KV cache for completed request.

    Returns:
        Amount of memory freed (MB)
    """
    ...


def get_total_kv_cache_gb(self) -> float:
    """Get total KV cache currently allocated."""
    return sum(e.kv_cache_mb for e in self.active_caches.values()) / 1024


def evict_idle_caches(self, max_age_seconds: float = 60.0) -> int:
    """
    Evict caches that have been idle too long.

    Called periodically and when under memory pressure.

    Returns:
        Number of caches evicted
    """
    ...
```

**Integration Points:**
- Called by: `ContextModelRouter`, `OverloadCoordinator`
- Integrates with: `ModelPoolManager` (eviction coordination)

---

### 2.4 Module: Journey Persistence Layer

**File:** `src/cohezion/swarm/journey_persistence.py`

**Purpose:** Dual-write agentic journeys to Vault MCP and SurrealDB for durability.

**Class:** `JourneyPersistenceManager`

**Key Attributes:**
```python
@dataclass
class JourneyCheckpoint:
    """Serializable checkpoint of journey state."""

    checkpoint_id: str
    journey_id: str
    agent_id: str
    timestamp: float

    # Journey state
    current_phase: str
    physics_state: dict  # 12D physics state
    step_count: int
    coherence_trajectory: list[float]

    # Context
    recent_actions: list[dict]
    active_skills: list[str]

    # Vault references
    vault_path: str
    surrealdb_id: str


class JourneyPersistenceManager:
    def __init__(
        self,
        mcp_client: MCPClient,
        surreal_client: SurrealClient,
        checkpoint_interval: int = 10,  # Steps between checkpoints
        vault_path_prefix: str = "agent-journeys",
    ):
        self.mcp = mcp_client
        self.surreal = surreal_client
        self.checkpoint_interval = checkpoint_interval
        self.vault_path_prefix = vault_path_prefix
        self._local_cache: dict[str, JourneyPoint] = {}  # Hot path cache
```

**Key Methods:**

```python
async def persist_journey_point(
    self, point: JourneyPoint, priority: PersistencePriority = PersistencePriority.NORMAL
) -> PersistenceResult:
    """
    Persist journey point to all storage layers.

    Storage Strategy:
    - Local Cache: Always (synchronous, <1ms)
    - SurrealDB: Async fire-and-forget (fast query path)
    - Vault MCP: Async with retry (durability, human-readable)

    Priority Levels:
    - CRITICAL: Block until all writes complete
    - NORMAL: Local + SurrealDB immediate, Vault async
    - BACKGROUND: All async, best effort

    Args:
        point: Journey point to persist
        priority: Persistence priority

    Returns:
        PersistenceResult with success status and paths
    """
    ...


async def create_checkpoint(
    self, journey_tracker: JourneyTracker, force: bool = False
) -> CheckpointResult:
    """
    Create journey checkpoint for session continuity.

    Called:
    - Every N steps (configurable)
    - At phase transitions
    - On graceful shutdown
    - When requested by agent

    Checkpoint stored in:
    - SurrealDB: agent_journeys table
    - Vault: checkpoints/{agent_id}/{journey_id}.json
    """
    ...


async def restore_from_checkpoint(self, agent_id: str, journey_id: str) -> JourneyTracker | None:
    """
    Restore journey tracker from checkpoint.

    Used for:
    - Session recovery after restart
    - Agent migration between nodes
    - Long-running journey continuation

    Returns:
        Restored JourneyTracker or None if no checkpoint found
    """
    ...


async def write_to_vault(self, journey_id: str, points: list[JourneyPoint]) -> str:
    """
    Write human-readable journey log to Vault MCP.

    Creates markdown document with:
    - Journey overview
    - Phase-by-phase breakdown
    - Physics state visualizations
    - Decision points with rationale

    Returns:
        Vault path to created document
    """
    ...
```

**Integration Points:**
- Called by: `JourneyTracker` (enhanced), `CompoundExecutor`
- Calls: `MCPClient.vault_write()`, `SurrealClient.store_node()`

---

### 2.5 Module: Enhanced Model Pool Manager

**File:** `src/cohezion/swarm/model_pool_manager.py` (Enhanced)

**Purpose:** 3-tier model lifecycle with graduated eviction and coordination.

**Enhancements to Existing:**

```python
class ModelPoolManager:
    def __init__(self, config: TierConfig | None = None):
        # ... existing init ...

        # NEW: Integration with Overload Coordinator
        self.overload_coordinator: OverloadCoordinator | None = None

        # NEW: KV cache awareness
        self.kv_cache_tracker: KVCacheTracker | None = None

        # NEW: Request coalescing
        self._loading_futures: dict[str, asyncio.Future[bool]] = {}

    def set_coordinator(self, coordinator: OverloadCoordinator) -> None:
        """Connect to overload protection system."""
        self.overload_coordinator = coordinator

    def set_kv_cache_tracker(self, tracker: KVCacheTracker) -> None:
        """Connect to KV cache management."""
        self.kv_cache_tracker = tracker


async def ensure_loaded(self, model_name: str) -> bool:
    """
    Enhanced model loading with coordination.

    NEW: Request Coalescing
    - If another request is loading the same model, wait for it
    - Prevents simultaneous loads of same model

    NEW: Coordination
    - Check with OverloadCoordinator before loading
    - Respect memory pressure limits
    """
    # Check if already loading
    if model_name in self._loading_futures:
        return await self._loading_futures[model_name]

    # Create future for coalescing
    future: asyncio.Future[bool] = asyncio.Future()
    self._loading_futures[model_name] = future

    try:
        # Check with coordinator
        if self.overload_coordinator:
            can_load = await self.overload_coordinator.check_can_load(model_name)
            if not can_load:
                future.set_result(False)
                return False

        # Proceed with load
        result = await self._do_load(model_name)
        future.set_result(result)
        return result
    finally:
        del self._loading_futures[model_name]


async def evict_under_pressure(self, pressure: float) -> list[str]:
    """
    Graduated eviction based on pressure level.

    Eviction Priority:
    1. Cold models (LRU) - always first
    2. Warm models (LRU) - if pressure > 0.85
    3. Hot models - NEVER evicted

    Returns:
        List of evicted model names
    """
    ...
```

---

## 3. DATABASE SCHEMAS

### 3.1 SurrealDB Schema for Agentic Journeys

```sql
-- Agent Journeys Table
DEFINE TABLE agent_journeys SCHEMAFULL;

DEFINE FIELD id ON TABLE agent_journeys TYPE string;
DEFINE FIELD agent_id ON TABLE agent_journeys TYPE string;
DEFINE FIELD journey_id ON TABLE agent_journeys TYPE string;
DEFINE FIELD start_time ON TABLE agent_journeys TYPE datetime DEFAULT time::now();
DEFINE FIELD end_time ON TABLE agent_journeys TYPE datetime;
DEFINE FIELD status ON TABLE agent_journeys TYPE string 
    ASSERT $value IN ['active', 'paused', 'completed', 'failed'];

-- Physics state tracking
DEFINE FIELD current_physics_state ON TABLE agent_journeys TYPE object;
DEFINE FIELD coherence_trajectory ON TABLE agent_journeys TYPE array<float>;
DEFINE FIELD efficiency_trajectory ON TABLE agent_journeys TYPE array<float>;

-- Checkpoint info
DEFINE FIELD last_checkpoint_time ON TABLE agent_journeys TYPE datetime;
DEFINE FIELD checkpoint_count ON TABLE agent_journeys TYPE int DEFAULT 0;
DEFINE FIELD vault_checkpoint_path ON TABLE agent_journeys TYPE string;

-- Indexes
DEFINE INDEX idx_agent_id ON TABLE agent_journeys FIELDS agent_id;
DEFINE INDEX idx_journey_status ON TABLE agent_journeys FIELDS status;
DEFINE INDEX idx_start_time ON TABLE agent_journeys FIELDS start_time;

-- Journey Phases Table (detailed step tracking)
DEFINE TABLE journey_phases SCHEMAFULL;

DEFINE FIELD id ON TABLE journey_phases TYPE string;
DEFINE FIELD journey_id ON TABLE journey_phases TYPE record<agent_journeys>;
DEFINE FIELD phase_number ON TABLE journey_phases TYPE int;
DEFINE FIELD phase_type ON TABLE journey_phases TYPE string 
    ASSERT $value IN ['planning', 'execution', 'review', 'retrospection'];
DEFINE FIELD timestamp ON TABLE journey_phases TYPE datetime DEFAULT time::now();

-- Physics state
DEFINE FIELD physics_state ON TABLE journey_phases TYPE object;
DEFINE FIELD position_3d ON TABLE journey_phases TYPE object;  -- {x, y, z}
DEFINE FIELD coherence ON TABLE journey_phases TYPE float ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD efficiency ON TABLE journey_phases TYPE float ASSERT $value >= 0 AND $value <= 1;

-- Context
DEFINE FIELD model_used ON TABLE journey_phases TYPE string;
DEFINE FIELD context_length ON TABLE journey_phases TYPE int;
DEFINE FIELD operation_type ON TABLE journey_phases TYPE string;
DEFINE FIELD duration_ms ON TABLE journey_phases TYPE float;

-- Indexes
DEFINE INDEX idx_journey_id ON TABLE journey_phases FIELDS journey_id;
DEFINE INDEX idx_phase_type ON TABLE journey_phases FIELDS phase_type;
DEFINE INDEX idx_timestamp ON TABLE journey_phases FIELDS timestamp;

-- Agent Decisions Table (audit trail)
DEFINE TABLE agent_decisions SCHEMAFULL;

DEFINE FIELD id ON TABLE agent_decisions TYPE string;
DEFINE FIELD journey_id ON TABLE agent_decisions TYPE record<agent_journeys>;
DEFINE FIELD decision_type ON TABLE agent_decisions TYPE string;
DEFINE FIELD timestamp ON TABLE journey_phases TYPE datetime DEFAULT time::now();

-- Decision content
DEFINE FIELD context ON TABLE agent_decisions TYPE object;
DEFINE FIELD options_considered ON TABLE agent_decisions TYPE array<object>;
DEFINE FIELD selected_option ON TABLE agent_decisions TYPE object;
DEFINE FIELD rationale ON TABLE agent_decisions TYPE string;

-- Outcome
DEFINE FIELD success ON TABLE agent_decisions TYPE bool;
DEFINE FIELD outcome_metrics ON TABLE agent_decisions TYPE object;

-- Vault reference
DEFINE FIELD vault_decision_path ON TABLE agent_decisions TYPE string;

-- Indexes
DEFINE INDEX idx_journey_decisions ON TABLE agent_decisions FIELDS journey_id;
DEFINE INDEX idx_decision_type ON TABLE agent_decisions FIELDS decision_type;
```

---

## 4. CONFIGURATION SPECIFICATION

### 4.1 Ollama Service Configuration

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Network
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"

# AMD Ryzen AI MAX+ 395 Specific
Environment="OLLAMA_NUM_THREADS=16"           # Half of 32 threads
Environment="OLLAMA_NUM_PARALLEL=3"            # Conservative for 128GB
Environment="OLLAMA_MAX_LOADED_MODELS=4"       # Hot + Warm tiers
Environment="OLLAMA_FLASH_ATTENTION=1"         # Reduce memory
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"        # Compress KV cache

# UMA Optimization
Environment="OLLAMA_GPU_OVERHEAD=0"            # No discrete GPU
Environment="OLLAMA_CPU_COUNT=32"              # All logical cores

# Scheduling
Environment="OLLAMA_SCHED_SPREAD=1"            # Spread across NUMA

# Resource Limits
MemoryMax=110G                                  # Leave 18GB system
CPUQuota=90%                                    # Leave 10% headroom

# Restart Policy
Restart=on-failure
RestartSec=5s
StartLimitInterval=60s
StartLimitBurst=3
```

### 4.2 Kernel Optimizations

```bash
# /etc/sysctl.d/99-cohezion-performance.conf

# Huge pages for large memory allocations
vm.nr_hugepages = 1024
vm.hugetlb_shm_group = 1000

# Memory management
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.vfs_cache_pressure = 50

# Network for Ollama API
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.core.netdev_max_backlog = 5000

# File descriptors
fs.file-max = 2097152
fs.nr_open = 2097152
```

### 4.3 Model Context Configuration

```python
# src/cohezion/swarm/context_config.py

CONTEXT_CONFIG = {
    # Memory allocation strategy for 128GB system
    "memory_budget": {
        "model_weights_max": 70.0,  # 70GB for model weights
        "kv_cache_max": 40.0,  # 40GB for KV cache
        "activation_buffer": 10.0,  # 10GB for activations
        "system_reserve": 8.0,  # 8GB for system
    },
    # Model-specific context limits
    "models": {
        "phi4-mini-reasoning:latest": {
            "native_context": 131072,
            "max_safe_context_128gb": 131072,
            "optimal_context": 65536,
            "min_viable_context": 4096,
            "kv_cache_mb_per_1k": 0.3,
        },
        "qwen3-coder-next:q4_K_M": {
            "native_context": 262144,
            "max_safe_context_128gb": 65536,  # Conservative
            "optimal_context": 32768,
            "min_viable_context": 8192,
            "kv_cache_mb_per_1k": 0.8,
        },
        "glm-4.7-flash:latest": {
            "native_context": 198000,
            "max_safe_context_128gb": 65536,
            "optimal_context": 32768,
            "min_viable_context": 4096,
            "kv_cache_mb_per_1k": 0.5,
        },
        "nemotron-3-nano:latest": {
            "native_context": 1000000,  # 1M theoretical
            "max_safe_context_128gb": 16384,  # HARD LIMIT
            "optimal_context": 8192,
            "min_viable_context": 4096,
            "kv_cache_mb_per_1k": 0.5,
            "warning": "Large context can OOM system - strictly limited",
        },
    },
    # Dynamic adjustment
    "dynamic_scaling": {
        "enable": True,
        "check_interval_seconds": 5,
        "scale_down_threshold": 0.75,  # Reduce at 75% pressure
        "scale_up_threshold": 0.50,  # Increase at 50% pressure
    },
}
```

---

## 5. IMPLEMENTATION ORDER

### Phase 1: Foundation (Week 1)
1. ✅ Create `OverloadCoordinator` with graduated response
2. ✅ Create `KVCacheTracker` for memory accounting
3. ✅ Enhance `ModelPoolManager` with coordination hooks
4. ✅ Update Ollama systemd configuration

### Phase 2: Routing (Week 2)
1. ✅ Create `ContextModelRouter` with context-aware selection
2. ✅ Create `ContextValidator` for request validation
3. ✅ Integrate with existing `SmartRouter`
4. ✅ Add context efficiency metrics

### Phase 3: Persistence (Week 3)
1. ✅ Create `JourneyPersistenceManager`
2. ✅ Implement SurrealDB schema updates
3. ✅ Add Vault MCP journey logging
4. ✅ Create checkpoint system
5. ✅ Implement cross-session continuity

### Phase 4: Integration (Week 4)
1. ✅ Wire all components together
2. ✅ Update `CompoundExecutor` to use new router
3. ✅ Update `JourneyTracker` for persistence
4. ✅ Add comprehensive error handling
5. ✅ Create integration tests

### Phase 5: Validation (Week 5)
1. ✅ Load testing at 70%, 80%, 90% memory pressure
2. ✅ Journey persistence failure testing
3. ✅ Context window stress testing
4. ✅ Circuit breaker coordination testing
5. ✅ Documentation and runbooks

---

## 6. TESTING SPECIFICATION

### 6.1 Unit Tests

```python
# tests/swarm/test_overload_coordinator.py


class TestOverloadCoordinator:
    async def test_graduated_response_65_percent(self):
        """At 65%, no action taken."""
        coordinator = OverloadCoordinator()
        action = await coordinator.handle_memory_pressure(0.65)
        assert action.level == ProtectionLevel.NORMAL
        assert len(action.actions) == 0

    async def test_graduated_response_75_percent(self):
        """At 75%, context reduced 25%."""
        coordinator = OverloadCoordinator()
        action = await coordinator.handle_memory_pressure(0.75)
        assert action.level == ProtectionLevel.WARNING
        assert "reduce_context_25" in action.actions

    async def test_graduated_response_95_percent(self):
        """At 95%, emergency restart triggered."""
        coordinator = OverloadCoordinator()
        action = await coordinator.handle_memory_pressure(0.95)
        assert action.level == ProtectionLevel.EMERGENCY
        assert "emergency_restart" in action.actions


# tests/swarm/test_kv_cache_tracker.py


class TestKVCacheTracker:
    def test_calculate_kv_size(self):
        """KV cache calculation is accurate."""
        tracker = KVCacheTracker()
        model = MODEL_PROFILES["qwen3-coder-next:q4_K_M"]
        kv_size = tracker.calculate_kv_size(model, 64000)
        # 64K context / 1K * 0.8 MB per 1K = 51.2 MB
        assert abs(kv_size - 51.2) < 1.0

    async def test_allocation_under_pressure(self):
        """Allocation fails gracefully when over limit."""
        tracker = KVCacheTracker(max_total_cache_gb=0.001)  # 1MB limit
        model = MODEL_PROFILES["phi4-mini-reasoning:latest"]

        result = await tracker.allocate("req1", model, 64000)
        assert result.success is False
        assert result.queue_position > 0
```

### 6.2 Integration Tests

```python
# tests/integration/test_context_routing.py


class TestContextRouting:
    async def test_small_context_routes_to_small_model(self):
        """2K context should prefer phi4-mini over qwen3-coder."""
        router = ContextModelRouter()
        request = RoutingRequest(context_length=2048, task_type="analysis", min_quality=0.7)

        decision = await router.route(request)
        assert "phi4" in decision.model_name  # Should select smaller model

    async def test_large_context_requires_large_model(self):
        """64K context requires model that supports it."""
        router = ContextModelRouter()
        request = RoutingRequest(context_length=65536, task_type="coding", min_quality=0.9)

        decision = await router.route(request)
        assert decision.model_name in ["qwen3-coder-next:q4_K_M", "glm-4.7-flash:latest"]
        assert decision.context_allocated >= 65536


# tests/integration/test_journey_persistence.py


class TestJourneyPersistence:
    async def test_dual_write_succeeds(self):
        """Journey point written to both Vault and SurrealDB."""
        manager = JourneyPersistenceManager(mcp_client=mock_mcp, surreal_client=mock_surreal)

        point = create_test_journey_point()
        result = await manager.persist_journey_point(point)

        assert result.local_cached is True
        assert result.surrealdb_stored is True
        assert result.vault_written is True

    async def test_checkpoint_recovery(self):
        """Journey can be restored from checkpoint."""
        manager = JourneyPersistenceManager(mcp_client=mock_mcp, surreal_client=mock_surreal)

        # Create and checkpoint
        tracker = create_test_journey()
        await manager.create_checkpoint(tracker)

        # Restore
        restored = await manager.restore_from_checkpoint(tracker.agent_id, tracker.journey_id)

        assert restored is not None
        assert restored.step_count == tracker.step_count
```

### 6.3 Load Tests

```python
# tests/load/test_memory_pressure.py


class TestMemoryPressure:
    async def test_70_percent_pressure_handles_gracefully(self):
        """System continues operating at 70% memory."""
        # Fill memory to 70%
        await fill_memory_to_percent(0.70)

        # Run 50 requests
        results = await run_concurrent_requests(50)

        # All should succeed
        assert all(r.success for r in results)
        # Context should be reduced for large models
        assert any(r.context_reduced for r in results)

    async def test_90_percent_pressure_emergency_response(self):
        """System enters emergency mode at 90%."""
        await fill_memory_to_percent(0.90)

        coordinator = OverloadCoordinator()
        action = await coordinator.handle_memory_pressure(0.90)

        assert action.level == ProtectionLevel.CRITICAL
        assert "evict_warm_models" in action.actions
        assert "queue_requests" in action.actions
```

---

## 7. MONITORING & OBSERVABILITY

### 7.1 Metrics to Track

```python
# Metrics exposed via Prometheus/Grafana

# System-level
memory_pressure_ratio gauge           # Current memory pressure
kv_cache_usage_gb gauge                 # Total KV cache used
active_models_count gauge               # Number of loaded models
request_queue_depth gauge               # Current queue depth

# Model-level
tokens_per_second histogram             # By model
context_efficiency_ratio gauge          # requested / allocated
model_load_time_seconds histogram       # Time to load each model
circuit_breaker_state gauge             # 0=closed, 1=open, 2=half-open

# Journey-level
journey_persistence_success counter     # Successful persists
journey_persistence_latency histogram   # Time to persist
checkpoint_creation_count counter       # Checkpoints created
journey_recovery_success gauge          # Successful recoveries

# Alert thresholds
ALERTS = {
    "memory_pressure_high": {
        "condition": "memory_pressure_ratio > 0.85",
        "severity": "warning",
        "action": "page_on_call",
    },
    "memory_pressure_critical": {
        "condition": "memory_pressure_ratio > 0.95",
        "severity": "critical",
        "action": "page_admin_immediately",
    },
    "kv_cache_near_limit": {
        "condition": "kv_cache_usage_gb > 35",
        "severity": "warning",
    },
    "journey_persistence_failures": {
        "condition": "rate(journey_persistence_success[5m]) < 0.95",
        "severity": "critical",
    },
}
```

### 7.2 Dashboard Panels

1. **System Health**
   - Memory pressure gauge (color: green/yellow/red)
   - KV cache usage bar
   - Active models timeline
   - Request queue depth sparkline

2. **Model Performance**
   - Tokens/second by model
   - Context efficiency heatmap
   - Load/unload events timeline
   - Circuit breaker states

3. **Journey Persistence**
   - Persistence success rate
   - Latency percentiles
   - Vault write success rate
   - SurrealDB query latency

4. **Alerts**
   - Active alerts list
   - Alert history timeline
   - Mean time to recovery (MTTR)

---

## 8. RUNBOOKS

### 8.1 Memory Pressure Response

```markdown
## Memory Pressure Alert Response

### Alert: memory_pressure_warning (75%)

1. Check current state:
   ```bash
   curl http://localhost:11434/api/ps
   ```

2. Review recent evictions:
   ```bash
   tail -f /var/log/cohezion/model_pool.log
   ```

3. If sustained > 80% for 5 minutes:
   - Identify memory-heavy requests
   - Consider manual eviction: `ollama stop <model>`

### Alert: memory_pressure_critical (92%)

1. **Immediate Actions** (automatic):
   - Cold models evicted
   - Warm models queued for eviction
   - New requests queued

2. **Manual Response**:
   ```bash
   # Check which models are loaded
   ollama ps
   
   # If qwen3-coder-next:q8_0 is loaded, consider unloading
   ollama stop qwen3-coder-next:q8_0
   ```

3. **Post-Incident**:
   - Review logs for root cause
   - Adjust thresholds if false positive
   - Document in incident tracker
```

### 8.2 Journey Persistence Failure

```markdown
## Journey Persistence Failure Response

### Symptoms
- "Journey persistence failed" error
- High latency on journey tracking
- Missing journey data in vault

### Response

1. Check Vault MCP connectivity:
   ```bash
   curl http://localhost:8360/health
   ```

2. Check SurrealDB connectivity:
   ```bash
   surreal health
   ```

3. If Vault MCP down:
   - System continues with local cache + SurrealDB
   - Check vault service logs
   - Restart vault MCP if needed

4. If SurrealDB down:
   - System continues with local cache + Vault
   - Check SurrealDB service
   - Circuit breaker will protect

5. **Data Recovery**:
   - Check local cache: `/tmp/cohezion/journey_cache/`
   - If available, manually sync to vault
   - If not available, journeys are lost for that session

### Prevention
- Monitor persistence success rate
- Alert if < 95% for 5 minutes
- Ensure redundant storage paths
```

---

## 9. APPENDIX

### 9.1 Glossary

- **KV Cache**: Key-Value cache used by transformer models for efficient inference
- **Agentic Journey**: Complete lifecycle of an agent's execution from start to finish
- **Context Window**: Maximum number of tokens a model can process at once
- **Memory Pressure**: Ratio of used memory to total available memory
- **Graduated Response**: Tiered response based on severity level

### 9.2 References

1. [Ollama Documentation - Configuration](https://github.com/ollama/ollama/blob/main/docs/faq.md)
2. [SurrealDB Schema Documentation](https://surrealdb.com/docs/surrealql)
3. [AMD Ryzen AI MAX+ 395 Specs](HARDWARE_PROFILE_PRIME.md)
4. [Adversarial Review](ADVERSARIAL_REVIEW_MODEL_SYSTEM.md)

### 9.3 Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-21 | Initial specification |

---

**Document Owner:** Platform Engineering Team  
**Review Cycle:** Quarterly  
**Next Review:** 2026-05-21
