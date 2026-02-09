# ResilientOllamaClient Analysis for Batching Integration

**Date**: 2026-02-08
**Purpose**: Document batching integration points and opportunities
**Source**: `src/cohezion/swarm/token_client.py`

## Executive Summary

The ResilientOllamaClient already has sophisticated features that support batching:
- SHA-256 prompt caching (eliminates duplicate requests)
- Phase 1 + Phase 2 batch processing (cache hits + parallel execution)
- Per-operation model routing
- Built-in retry logic and timeout management

The client is **well-positioned for advanced batching**, but there are integration opportunities for request coalescing, dynamic batch sizing, and thermal-aware scheduling.

## Current Architecture

### ResilientOllamaClient Capabilities

**1. Connection Management**
- Base URL configuration (default: http://localhost:11434)
- Configurable timeout (default: 300 seconds)
- Exponential backoff retry logic (default: 3 retries)
- Automatic response validation

**2. Request Handling**
- Supports prompt, system, and model parameters
- Configurable num_predict (tokens to generate)
- Async/await support for non-blocking calls
- Returns (response_text, tokens_used) tuple

**3. Rate Limiting & Queueing**
- Internal rate limiting (prevents API flooding)
- Concurrent request handling
- Model loading overhead management

**4. Error Handling**
```python
Handles:
- Connection timeouts (retries with backoff)
- Invalid responses (validation)
- Model unavailability (fallback logic)
- Rate limit errors (queue management)
```

### Batch Processing Features

**BatchProcessor** (companion class)
- Phase 1: Cache lookup (zero-cost)
- Phase 2: Parallel execution of cache misses
- AsyncIO concurrency gating
- Metrics collection (cache hits, total tokens, latency)

**BatchItem** Structure
```python
BatchItem(
    id="unique_id",
    prompt="user input",
    system="system prompt",
    model="model_name"
)
```

## Integration Opportunities

### 1. Request Coalescing Integration

**Current State**:
- SHA-256 caching handles exact duplicates
- No soft coalescing (similar-but-not-identical requests)

**Integration Point**:
- Add RequestCoalescer before batch_generate()
- Merge similar prompts using Jaccard similarity
- Return results mapped back to original requests

**Implementation Strategy**:
```python
# In batch_generate():
1. Apply RequestCoalescer to input batch
2. Process coalesced batch (fewer actual requests)
3. Map results back to original requests
4. Return combined response
```

**Expected Benefit**: 50-90% reduction in actual API calls for duplicate/similar requests

### 2. Dynamic Batch Sizing

**Current State**:
- Batch size fixed at call time
- No constraint on max concurrent requests

**Integration Point**:
```python
class BatchResult:
    cache_hits: int  # Available for next batch decision
    total_tokens: int  # Track token usage
    latency_ms: float  # Measure actual performance
```

**Integration Strategy**:
- Measure actual VRAM usage after batch executes
- Use batch_sizing heuristics to adjust next batch size
- Feed metrics back to adaptive sizing

**Implementation**:
```python
result = await client.batch_generate(items)
next_batch_size = calculate_batch_size(
    context_length=avg_context,
    vram_available_mb=get_vram_available(),
    model_name=items[0].model
)
```

### 3. Thermal-Aware Scheduling

**Current State**:
- No thermal awareness
- Doesn't adapt to system thermal state

**Integration Point**:
- Monitor thermal state between batches
- Reduce batch size or add delays if thermal pressure high
- Report thermal pressure in BatchResult metadata

**Implementation**:
```python
hw_state = get_hardware_state()
if hw_state.thermal_percent > 75:
    # Reduce batch size or add cooling delay
    batch_size = max(1, batch_size // 2)
    await asyncio.sleep(5)  # Let system cool
```

### 4. Model Loading Overhead Measurement

**Current State**:
- Model loading handled internally
- No exposed metrics on load overhead

**Integration Point**:
- Measure first inference vs. subsequent
- Cache model state to avoid reloads
- Add model_load_time to metrics

**Implementation**:
```python
# Track if model is cold (first load) vs warm
class ModelState:
    name: str
    is_loaded: bool
    load_time_ms: float
    last_used: datetime
```

## Rate Limiting Analysis

**Current Behavior**:
- No explicit rate limit configuration
- Ollama default: ~4 concurrent requests per GPU
- Queuing happens naturally through async/await

**Batching Impact**:
- Larger batches = fewer concurrent model invocations
- Single batch of 4 = same as 4 serial requests in parallel
- Reduces context switching overhead

**Recommendation**:
- Keep current async/await concurrency model
- Let batching naturally limit concurrency
- Add soft limits if needed via semaphore

## Error Handling & Resilience

**Current Features**:
1. **Retry Logic**
   - Exponential backoff on failure
   - Configurable max retries

2. **Timeout Management**
   - Per-request timeout
   - Prevents hanging on slow models

3. **Response Validation**
   - Checks for valid JSON
   - Validates response structure

**Batching Resilience**:
- Partial batch failure: Retry individual items
- Full batch failure: Fallback to smaller batches
- Cascading failures: Degrade to single-request mode

## Model Switching & Fallback

**Current Support**:
- Per-request model selection
- Different models in same batch

**Implications for Batching**:
- Can coalesce requests for different models (but process separately)
- BatchProcessor already handles per-model routing
- Reduces benefit of pure request merging

**Recommendation**:
- Group batch by model first
- Apply coalescing within model groups
- Process each group independently

## Integration Roadmap

### Phase 1: Metrics Enhancement (Immediate)
- [ ] Add coalescing metrics to BatchResult
- [ ] Track model load times
- [ ] Measure thermal impact per batch

### Phase 2: Request Coalescing (This Sprint)
- [ ] Integrate RequestCoalescer into batch_generate()
- [ ] Map results back to original requests
- [ ] Validate coalescing correctness

### Phase 3: Dynamic Sizing (Follow-up)
- [ ] Feed actual VRAM usage to batch_sizing
- [ ] Adapt batch size based on performance
- [ ] Auto-tune window size

### Phase 4: Thermal Awareness (Follow-up)
- [ ] Monitor thermal state
- [ ] Reduce batch size under thermal pressure
- [ ] Add cooling delays when needed

## Key Integration Points

### 1. Before batch_generate()
```python
# Apply coalescing
coalesced_batch = coalescer.coalesce(batch)

# Calculate safe batch size
safe_size = calculate_batch_size(
    context_length=get_avg_context(batch),
    vram_available_mb=get_vram_available(),
    model=coalesced_batch[0].model
)

# Split if needed
sub_batches = split_batch(coalesced_batch, safe_size)
```

### 2. Inside batch_generate()
```python
# Track per-model performance
for model_group in group_by_model(sub_batches):
    result = await process_group(model_group)
    metrics.record_model_performance(model_group.model, result)
```

### 3. After batch_generate()
```python
# Map results back to original requests
result_mapping = coalescer.get_result_mapping()
final_results = map_back_to_originals(result, result_mapping)

# Feed metrics for next batch
next_batch_size = suggest_batch_size(result.metrics)
```

## Performance Expectations

### Baseline (No Coalescing)
- 100 requests → 100 API calls
- Throughput: 10 req/min × 10 tok/req = 100 tok/min

### With Coalescing (50% reduction)
- 100 requests → 50 API calls (50 duplicates eliminated)
- Throughput: 150 tok/min (1.5x improvement)

### With Batching (Size 4)
- 100 requests → 25 batches
- Better parallelism: 150 tok/min → 200 tok/min

### With All Optimizations
- Coalescing + batching + thermal awareness
- Expected: 3-5x improvement
- Target: 300-500 tok/min

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Coalescing overhead > benefit | Start with exact dedup (no Jaccard) |
| Batch timeout for slow models | Per-model timeout, partial results |
| Thermal throttling mid-batch | Monitor temperature, split batch |
| Memory fragmentation from large batches | Use dynamic sizing, monitor RSS |
| Model switching latency | Group by model before batching |

## Recommendations

1. **Start with metrics**: Add instrumentation to measure current performance
2. **Add coalescing gradually**: Start with exact dedup, then soft coalescing
3. **Respect concurrency limits**: Honor Ollama's 4-request limit per GPU
4. **Prioritize thermal**: Temperature is bottleneck on iGPU, address first
5. **Measure everything**: Every optimization needs baseline + improvement proof

## Files to Modify/Create

**Minimal Changes**:
- Extend `BatchResult` dataclass to include coalescing metrics
- Add optional `RequestCoalescer` parameter to batch_generate()

**New Components**:
- RequestCoalescer → batch_optimizer.py
- batch_sizing → batch_sizing.py
- HardwareProfiler integration stub

## Conclusion

ResilientOllamaClient is **well-designed for batching integration**. The existing architecture already supports:
- Parallel request execution
- Per-model routing
- Cache optimization
- Retry resilience

The integration points are clean and clear. Advanced batching (coalescing + dynamic sizing + thermal awareness) can be added incrementally without major refactoring.

**Estimated integration effort**: 2-3 sprint cycles for full optimization stack
**Expected ROI**: 3-5x throughput improvement demonstrated through profiling
