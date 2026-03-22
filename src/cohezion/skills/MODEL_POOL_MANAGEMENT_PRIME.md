# MODEL_POOL_MANAGEMENT_PRIME

## Purpose
Manage the lifecycle of local Ollama models across hot/warm/cold tiers, ensuring the CostAwareRouter only routes to loaded, healthy models.

## Trigger
- System startup (initialize pool from tier config)
- Before model selection (ensure target model is loaded)
- Periodic health check (every 5 minutes by default)
- Memory pressure exceeds threshold (evict cold/warm models)

## Tier Definitions

| Tier | Behavior | keep_alive | Evictable |
|------|----------|------------|-----------|
| HOT  | Always loaded, never evicted | -1 (infinite) | No |
| WARM | Loaded at startup, evicted under memory pressure | 300s | Yes (last resort) |
| COLD | On-demand only, evicted after idle timeout | 0 (immediate) | Yes (first priority) |

## Default Roster

- **HOT**: phi4-mini-reasoning, nomic-embed-text (fast inference + embeddings)
- **WARM**: glm-4.7-flash, qwen3-coder:30b (general + code tasks)
- **COLD**: deepcoder:14b, nemotron-3-nano (on-demand specialists)

## Algorithm: ensure_loaded(model)

```
1. If model.loaded AND model.healthy → return True (fast path)
2. If loaded_count >= max_concurrent_loaded:
   a. Find eviction candidate (cold first, then warm by LRU)
   b. Evict candidate via keep_alive=0
3. POST /api/generate with keep_alive based on tier
4. Health check: trivial prompt, verify response
5. Update PooledModel state
```

## Algorithm: demote_under_pressure()

```
1. memory_pressure = 1 - (available_gb / total_gb)
2. If pressure < threshold → no action
3. Sort loaded models by eviction priority:
   - COLD models first (by last_used ascending)
   - WARM models second (by last_used ascending)
   - HOT models never evicted
4. Evict until pressure < threshold or only HOT models remain
```

## Integration Points

- **CostAwareRouter**: `pool_manager.get_available_models()` filters routing candidates
- **MemoryBandwidthAnalyzer**: Reused for memory pressure calculation
- **OllamaModelManager**: Coexists — pool manages lifecycle, manager handles benchmarks

## Constraints

- Global Ollama concurrency limit: 4 models max
- Memory: 128 GiB total, aim for <80% utilization
- Health checks: non-blocking, <5s timeout per model
- All state transitions logged for observability

## Anti-Patterns

- Routing to unloaded models (causes cold-start latency spikes)
- Evicting HOT models under any circumstances
- Health-checking models that aren't loaded
- Loading models without checking memory pressure first

## Success Metrics

| Metric | Target |
|--------|--------|
| Cold-start avoidance | >95% of requests hit loaded models |
| Memory utilization | <80% under normal load |
| Health check latency | <5s per model |
| Eviction accuracy | Cold models evicted before warm |

## References

- `src/cohezion/swarm/model_pool_manager.py` — Core implementation
- `src/cohezion/swarm/model_pool_config.py` — Configuration and data models
- `src/cohezion/swarm/dynamic_model_router.py:60` — MemoryBandwidthAnalyzer
- `src/cohezion/swarm/model_manager.py` — OllamaModelManager (coexists)
