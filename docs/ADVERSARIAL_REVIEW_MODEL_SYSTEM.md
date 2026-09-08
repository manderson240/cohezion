# ADVERSARIAL REVIEW: Model Management & Agentic Journey System

**Date:** 2026-02-21  
**Platform:** AMD Ryzen AI MAX+ 395 (128GB LPDDR5X-8000)  
**Review Type:** Security & Performance Audit  

---

## EXECUTIVE SUMMARY

**Status:** ⚠️ CRITICAL GAPS IDENTIFIED

The current implementation has significant architectural gaps that could lead to:
1. System instability under load
2. Memory exhaustion without graceful degradation
3. Lost agentic journey data during failures
4. Suboptimal model selection leading to token waste

**Recommendation:** Immediate implementation of safeguards and vault integration.

---

## 1. CRITICAL VULNERABILITIES

### 1.1 Context Window Mismatch (CRITICAL)

**Issue:** `dynamic_model_router.py` hardcodes `num_ctx` without considering KV cache memory requirements.

**Current Code:**
```python
# Line 419 in dynamic_model_router.py
"options": {
    "num_ctx": max_context,  # No KV cache calculation
    "temperature": request.get("temperature", 0.7),
    ...
}
```

**Attack Vector:**
- User requests 256K context on `qwen3-coder-next:q8_0` (85GB model)
- KV cache = 256K * 80B params * 2 bytes * layers ≈ 16GB
- Total memory: 85GB + 16GB + activation ≈ 105GB
- **System crashes with OOM at 128GB limit**

**Impact:** Complete system failure, data loss

**Fix Required:** 
```python
# Calculate safe context based on available memory
kv_cache_gb = (max_context / 1000) * model_params_billions * 0.5
safe_context = min(max_context, (available_memory_gb * 0.8 - model_size_gb) / kv_per_1k)
```

---

### 1.2 No Graduated Memory Response (CRITICAL)

**Issue:** `model_pool_manager.py` has binary threshold (80%) without intermediate actions.

**Current Code:**
```python
# Line 263-264 in model_pool_manager.py
pressure = self._memory.analyze_memory_pressure()
if pressure < self._config.memory_pressure_threshold:  # Only one threshold
    return []
```

**Attack Vector:**
- Memory pressure slowly climbs from 70% → 95%
- No action until 80%, then everything evicts at once
- Hot models evicted unnecessarily
- **System thrashing instead of graceful degradation**

**Impact:** Performance degradation, hot cache loss

**Fix Required:**
```python
# Graduated response
if pressure > 0.95:
    emergency_restart()
elif pressure > 0.85:
    evict_cold() + reduce_context(75%)
elif pressure > 0.75:
    evict_cold() + reduce_context(50%)
elif pressure > 0.65:
    reduce_context(25%)
```

---

### 1.3 Vault Journey Data Loss (CRITICAL)

**Issue:** `journey_tracker.py` persists to local files, not vault MCP, with no redundancy.

**Current Code:**
```python
# Lines 540-550 in journey_tracker.py (implied from executor.py usage)
# Journey points stored locally only
```

**Attack Vector:**
- Container/pod restarts
- Disk failure
- Migration to new node
- **All agentic journey data lost**

**Impact:** Loss of agent learning, inability to trace decisions

**Fix Required:**
```python
# Dual-write to vault MCP and SurrealDB
async def persist_journey_point(self, point: JourneyPoint):
    # Local cache for speed
    await self._local_cache.store(point)

    # Async vault write for durability
    asyncio.create_task(
        self._mcp_client.vault_write(
            f"journeys/{point.agent_id}/{point.timestamp}.json", point.to_json()
        )
    )

    # SurrealDB for querying
    asyncio.create_task(self._surreal_client.store_node(point.to_universe_node()))
```

---

### 1.4 Circuit Breaker Blind Spots (HIGH)

**Issue:** Circuit breakers track failures but don't consider memory pressure or model-specific patterns.

**Current Code:**
```python
# model_fallback_strategy.py
failure_threshold = 3  # Fixed threshold for all models
```

**Attack Vector:**
- Large model (85GB) fails once due to memory pressure
- Circuit breaker opens immediately
- System falls back to smaller model unnecessarily
- **Token efficiency destroyed**

**Impact:** Suboptimal model selection, wasted tokens

**Fix Required:**
```python
# Model-specific thresholds with memory awareness
CIRCUIT_CONFIG = {
    "qwen3-coder-next:q8_0": {
        "failure_threshold": 5,  # More lenient (larger model)
        "memory_sensitive": True,  # Don't count memory-related failures
        "latency_threshold_ms": 60000,
    },
    "phi4-mini-reasoning": {
        "failure_threshold": 3,
        "memory_sensitive": False,
        "latency_threshold_ms": 15000,
    },
}
```

---

## 2. ARCHITECTURAL GAPS

### 2.1 No Context-Aware Model Selection

**Issue:** Router selects model based on task type, not actual context needs.

**Current:**
- User needs 2K context for simple task
- Router selects based on "coding" → `qwen3-coder-next:q8_0`
- **Wastes 84GB of memory for 2K context**

**Fix:** Context-aware routing
```python
if context_length < 4096 and task_complexity < 0.5:
    return "phi4-mini-reasoning"  # 3.2GB, perfect fit
elif context_length < 32768:
    return "qwen3-coder:14b"  # Much smaller than 80B
```

---

### 2.2 Missing KV Cache Management

**Issue:** No tracking of KV cache usage across requests.

**Impact:**
- 3 concurrent requests each with 64K context
- Total KV cache: 3 × 16GB = 48GB
- Plus model weights = 100GB+
- **OOM despite model fitting in memory**

**Fix:** KV cache accounting
```python
class KVCacheTracker:
    def __init__(self):
        self.active_caches: dict[str, float] = {}  # model -> GB used
    
    def allocate(self, model: str, context_length: int) -> bool:
        kv_needed = self._calculate_kv_size(model, context_length)
        if self._available_memory() < kv_needed:
            return False
        self.active_caches[model] = kv_needed
        return True
```

---

### 2.3 No Agentic Journey Continuity

**Issue:** Agent journeys are session-scoped, not persisted across restarts.

**Current Flow:**
1. Agent starts journey tracking
2. Mid-journey: system restarts
3. Journey state lost
4. Agent starts from scratch

**Impact:** Repeated work, inability to learn from past journeys

**Fix:** Checkpoint-based journey persistence
```python
# Every N steps or at key milestones
async def checkpoint_journey(self):
    checkpoint = {
        "agent_id": self.agent_id,
        "journey_id": self.journey_id,
        "current_phase": self.current_phase,
        "physics_state": self.physics_state.to_dict(),
        "step_count": len(self.points),
        "timestamp": time.time(),
    }

    # Write to vault for durability
    await self._mcp.vault_write(
        f"checkpoints/{self.agent_id}/{self.journey_id}.json", json.dumps(checkpoint)
    )
```

---

### 2.4 Overload Protection Gaps

**Issue:** Multiple protection systems don't coordinate.

**Current Systems:**
- `QuantumPerformanceMonitor` (quantum_performance_monitor.py)
- `ModelPoolManager` eviction (model_pool_manager.py)
- Circuit breakers (model_fallback_strategy.py)
- Memory pressure detection (dynamic_model_router.py)

**Problem:** They operate independently, can conflict

**Fix:** Unified Overload Protection Coordinator
```python
class OverloadProtectionCoordinator:
    """Central coordination for all overload protection systems."""
    
    async def handle_memory_pressure(self, pressure: float):
        # Coordinate all systems
        if pressure > 0.90:
            await self._emergency_response()
        elif pressure > 0.80:
            await self._evict_and_throttle()
        elif pressure > 0.70:
            await self._graceful_degradation()
```

---

## 3. PERFORMANCE BOTTLENECKS

### 3.1 No Request Batching

**Issue:** Each request loads model independently if not hot.

**Current:**
- 3 concurrent requests for same model
- Each triggers `ensure_loaded()`
- Race condition: all 3 try to load simultaneously
- **3× memory usage spike**

**Fix:** Request coalescing
```python
class ModelLoadCoordinator:
    def __init__(self):
        self._loading: dict[str, asyncio.Future] = {}
    
    async def ensure_loaded(self, model: str) -> bool:
        if model in self._loading:
            # Wait for existing load operation
            return await self._loading[model]
        
        # Start new load operation
        future = asyncio.Future()
        self._loading[model] = future
        
        try:
            result = await self._do_load(model)
            future.set_result(result)
            return result
        finally:
            del self._loading[model]
```

---

### 3.2 Inefficient Model Preloading

**Issue:** Hot models loaded at startup without considering actual usage patterns.

**Current:**
```python
hot_models: list[str] = [
    "phi4-mini-reasoning:latest",
    "nomic-embed-text:latest",
]
```

**Problem:** 
- If system restarts, both load immediately
- 128GB system with 3.2GB + 0.6GB = 3.8GB used
- User only needs embeddings → wasted 3.2GB

**Fix:** Usage-pattern-based preloading
```python
class AdaptivePreloader:
    def __init__(self):
        self.usage_patterns: dict[str, list[datetime]] = {}

    def should_preload(self, model: str) -> bool:
        # Only preload if used in last hour
        recent_uses = [
            t for t in self.usage_patterns.get(model, []) if (datetime.now() - t).hours < 1
        ]
        return len(recent_uses) > 3  # Used 3+ times in last hour
```

---

## 4. INTEGRATION GAPS

### 4.1 Vault MCP Not Used for Journey Data

**Current:** Journey data stored in:
- Local files
- SurrealDB (if available)

**Missing:** Vault MCP for:
- Human-readable journey logs
- Cross-session agent memory
- Decision audit trails

**Fix:**
```python
class VaultJourneyLogger:
    async def log_journey_phase(self, phase: JourneyPhase):
        # Create human-readable markdown
        md_content = f"""# Journey Phase: {phase.name}

**Agent:** {phase.agent_id}  
**Timestamp:** {phase.timestamp}  
**Coherence:** {phase.coherence:.2f}  

## Context
{phase.context}

## Actions
{self._format_actions(phase.actions)}

## Physics State
```json
{phase.physics_state.to_json()}
```
"""
        
        # Write to vault
        await self._mcp.vault_write(
            f"agent-journeys/{phase.agent_id}/{phase.timestamp}.md",
            md_content
        )
```

---

### 4.2 SurrealDB Schema Incomplete for Agentic Journeys

**Current Schema:** Only `universe_nodes` table defined

**Missing:**
- `agent_journeys` table for journey tracking
- `journey_phases` table for phase details
- `agent_decisions` table for decision audit

**Fix:**
```sql
DEFINE TABLE agent_journeys SCHEMAFULL;
DEFINE FIELD id ON TABLE agent_journeys TYPE string;
DEFINE FIELD agent_id ON TABLE agent_journeys TYPE string;
DEFINE FIELD start_time ON TABLE agent_journeys TYPE datetime;
DEFINE FIELD end_time ON TABLE agent_journeys TYPE datetime;
DEFINE FIELD coherence_trajectory ON TABLE agent_journeys TYPE array;
DEFINE FIELD final_physics_state ON TABLE agent_journeys TYPE object;
DEFINE FIELD vault_path ON TABLE agent_journeys TYPE string;
DEFINE INDEX idx_agent_id ON TABLE agent_journeys FIELDS agent_id;
```

---

## 5. SECURITY CONCERNS

### 5.1 No Request Validation

**Issue:** Ollama requests accept arbitrary `num_ctx` values.

**Attack:**
```bash
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "phi4-mini", "prompt": "test", "options": {"num_ctx": 10000000}}'
```

**Impact:** Single request can OOM system

**Fix:** Context validation middleware
```python
class RequestValidator:
    MAX_CONTEXT = {
        "phi4-mini-reasoning:latest": 131072,
        "qwen3-coder-next:q4_K_M": 65536,
        "qwen3-coder-next:q8_0": 32768,
    }
    
    def validate_context(self, model: str, requested: int) -> int:
        max_allowed = self.MAX_CONTEXT.get(model, 32768)
        return min(requested, max_allowed)
```

---

### 5.2 Model Pool Bypass Possible

**Issue:** Direct Ollama calls bypass pool management.

**Current:**
- `smart_router.py` uses pool
- But any code can call Ollama directly
- **Pool state becomes inconsistent**

**Fix:** Enforced routing
```python
class OllamaProxy:
    """All Ollama calls must go through this proxy."""
    
    async def generate(self, request: dict) -> dict:
        # Validate through pool manager
        model = request["model"]
        if not await self._pool.ensure_loaded(model):
            raise ModelNotAvailable(model)
        
        # Validate context
        validated_request = self._validator.validate(request)
        
        # Track for journey
        await self._journey_tracker.track_request(validated_request)
        
        # Execute
        return await self._ollama.generate(validated_request)
```

---

## 6. RECOMMENDED IMMEDIATE ACTIONS

### Priority 1: System Stability
1. ✅ Implement graduated memory pressure response
2. ✅ Add KV cache size calculations
3. ✅ Create unified overload protection coordinator
4. ✅ Add request context validation

### Priority 2: Data Durability
1. ✅ Implement vault MCP journey persistence
2. ✅ Add SurrealDB agent_journeys table
3. ✅ Create journey checkpoint system
4. ✅ Add cross-session journey continuity

### Priority 3: Performance
1. ✅ Implement request coalescing
2. ✅ Add adaptive preloading
3. ✅ Create context-aware model selection
4. ✅ Optimize context window scaling

### Priority 4: Observability
1. ✅ Add KV cache metrics
2. ✅ Track context efficiency per model
3. ✅ Monitor journey persistence success rate
4. ✅ Create memory pressure dashboard

---

## 7. SPECIFICATION PRIORITIES

Based on this review, the implementation must address:

1. **Context-Aware Model Router** with KV cache accounting
2. **Vault-Integrated Journey Tracking** with dual-write durability
3. **Graduated Overload Protection** with coordinated response
4. **Agentic Journey Persistence** across sessions
5. **Request Validation** to prevent OOM attacks

---

**Reviewer:** Claude (Adversarial Review Mode)  
**Next Step:** Create detailed technical specifications for Priority 1 items.
