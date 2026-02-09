# Phase 1 Implementation Plan: Quick Wins (1-2 Days)

**Target**: 1.81× baseline improvement through concurrency, persistence, and LRU eviction
**Timeline**: 1-2 sprint days
**Risk Level**: Low (thermal safety built-in)
**Expected Impact**: 45% + 15% + additional gains = 1.81× baseline

## Overview

Phase 1 addresses the highest-ROI bottlenecks from research-analyst's findings:
1. **Concurrency ceiling**: Remove hardcoded limit of 4, scale to 8-12 safely
2. **Persistent cache**: Add JSONL persistence + session restore
3. **LRU eviction**: Implement cache eviction tracking and optimization

All components use our parallel infrastructure (metrics_collector, batch_sizing, profiler stub).

---

## Bottleneck #1: Concurrency Ceiling (45% Gain)

### Current State
- Hardcoded concurrency limit: 4 requests
- Hardware capable of 8-12 safely
- No thermal awareness of limit
- Wastes iGPU and memory capacity

### Solution: Dynamic Concurrency Gates

**Location**: ResilientOllamaClient or TokenEfficientClient

**Implementation**:
```python
from cohezion.swarm.metrics_collector import HardwareMetrics
from cohezion.swarm.hardware_profiler_stub import HardwareProfilerFactory

class DynamicConcurrencyGate:
    """Safely increases concurrency based on hardware state."""

    def __init__(self):
        self.metrics = HardwareMetrics()
        self.profiler = HardwareProfilerFactory.get_profiler()
        self.base_concurrency = 4

    def get_safe_concurrency(self) -> int:
        """Calculate safe concurrency for current hardware state."""
        state = self.metrics.get_snapshot()

        # Start conservative
        if not state.is_healthy():
            return self.base_concurrency  # Fall back to 4

        # Increase based on headroom
        if state.vram.used_percent < 60 and state.thermal.thermal_percent < 70:
            return 12  # Plenty of headroom
        elif state.vram.used_percent < 70 and state.thermal.thermal_percent < 75:
            return 10  # Good headroom
        elif state.vram.used_percent < 80 and state.thermal.thermal_percent < 80:
            return 8   # Moderate headroom
        else:
            return self.base_concurrency  # Stay at 4

    async def acquire(self) -> AsyncContextManager:
        """Acquire concurrency slot with safety checks."""
        max_conc = self.get_safe_concurrency()
        semaphore = asyncio.Semaphore(max_conc)
        async with semaphore:
            yield
```

**Integration Points**:
- Replace hardcoded 4 with dynamic gate
- Check before starting new requests
- Log concurrency changes for monitoring
- Fall back to 4 under thermal stress

**Validation**:
- Test scale 4→8 with metrics_collector monitoring
- Verify thermal doesn't spike
- Measure request throughput improvement
- Expected: ~45% throughput gain

**Files to Modify**:
- `src/cohezion/swarm/token_client.py` or `ResilientOllamaClient`

**Owner**: integration-engineer or performance-engineer

**Effort**: 2-4 hours

---

## Bottleneck #2: Persistent JSONL Cache (15% Gain)

### Current State
- Cache is in-memory only
- Lost on process restart
- No session recovery
- Cannot share cache between sessions

### Solution: JSONL Persistence + Session Restore

**Location**: New `src/cohezion/swarm/persistent_cache.py`

**Implementation**:
```python
import json
from pathlib import Path
from datetime import datetime

class PersistentCache:
    """JSONL-backed cache with session restore."""

    def __init__(self, cache_file: Path = Path("cache_session.jsonl")):
        self.cache_file = cache_file
        self.memory_cache = {}
        self.load_from_disk()

    def load_from_disk(self) -> None:
        """Restore cache from JSONL on startup."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    cache_key = entry["key"]
                    self.memory_cache[cache_key] = {
                        "value": entry["value"],
                        "hits": entry.get("hits", 0),
                        "timestamp": entry.get("timestamp"),
                    }
            logger.info(f"Loaded {len(self.memory_cache)} cache entries from disk")
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")

    def get(self, key: str) -> str | None:
        """Get value from cache (memory)."""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            entry["hits"] = entry.get("hits", 0) + 1
            self.persist_entry(key, entry)
            return entry["value"]
        return None

    def set(self, key: str, value: str) -> None:
        """Set value in cache (memory + disk)."""
        entry = {
            "key": key,
            "value": value,
            "hits": 0,
            "timestamp": datetime.now().isoformat(),
        }
        self.memory_cache[key] = entry
        self.persist_entry(key, entry)

    def persist_entry(self, key: str, entry: dict) -> None:
        """Persist single entry to JSONL."""
        try:
            with open(self.cache_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist cache entry: {e}")

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_hits = sum(e.get("hits", 0) for e in self.memory_cache.values())
        total_entries = len(self.memory_cache)
        return total_hits / total_entries if total_entries > 0 else 0.0

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "entries": len(self.memory_cache),
            "hit_rate": self.get_hit_rate(),
            "total_hits": sum(e.get("hits", 0) for e in self.memory_cache.values()),
            "cache_file": str(self.cache_file),
        }
```

**Integration Points**:
- Replace in-memory cache in TokenEfficientClient
- Load on startup (session restore)
- Persist on every write
- Measure hit rate improvements

**Validation**:
- Verify JSONL format matches baseline_profiler
- Test session restore (kill process, restart, check hits)
- Measure hit rate increase (expect 15% throughput gain)
- Monitor disk I/O (should be minimal)

**Files to Create**:
- `src/cohezion/swarm/persistent_cache.py` (new)

**Files to Modify**:
- `src/cohezion/swarm/token_client.py` (replace cache backend)

**Owner**: integration-engineer

**Effort**: 4-6 hours

---

## Bottleneck #3: LRU Eviction (Combined 1.81× Gain)

### Current State
- No cache eviction policy
- Cache grows unbounded
- Memory pressure not tracked
- No selective pruning

### Solution: LRU Eviction with Metrics

**Location**: Extend `PersistentCache` with eviction

**Implementation**:
```python
from collections import OrderedDict

class LRUPersistentCache(PersistentCache):
    """JSONL cache with LRU eviction policy."""

    def __init__(
        self,
        cache_file: Path = Path("cache_session.jsonl"),
        max_entries: int = 10000,
        eviction_threshold: float = 0.9,
    ):
        super().__init__(cache_file)
        self.max_entries = max_entries
        self.eviction_threshold = eviction_threshold
        self.access_order = OrderedDict()

    def get(self, key: str) -> str | None:
        """Get with LRU tracking."""
        result = super().get(key)
        if result is not None:
            # Move to end (most recently used)
            if key in self.access_order:
                self.access_order.move_to_end(key)
            else:
                self.access_order[key] = True
        return result

    def set(self, key: str, value: str) -> None:
        """Set with eviction checking."""
        # Check if eviction needed
        if len(self.memory_cache) > self.max_entries * self.eviction_threshold:
            self._evict_lru()

        super().set(key, value)
        self.access_order[key] = True

    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        target_size = int(self.max_entries * 0.8)
        to_evict = len(self.memory_cache) - target_size

        for _ in range(to_evict):
            if self.access_order:
                # Remove oldest (first item)
                oldest_key = next(iter(self.access_order))
                del self.memory_cache[oldest_key]
                del self.access_order[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")

    def get_eviction_metrics(self) -> dict:
        """Get eviction statistics."""
        return {
            "max_entries": self.max_entries,
            "current_entries": len(self.memory_cache),
            "utilization_percent": (len(self.memory_cache) / self.max_entries) * 100,
            "eviction_threshold": self.eviction_threshold,
        }
```

**Integration with Metrics**:
```python
# In metrics_collector or metrics_callback
metrics.record_cache_stats(
    entries=cache.get_eviction_metrics()["current_entries"],
    hit_rate=cache.get_hit_rate(),
    evictions_performed=cache.eviction_count,
)
```

**Validation**:
- Monitor VRAM usage before/after
- Measure hit rate stability (should not drop)
- Verify eviction happens at threshold
- Measure combined throughput gain (1.81× baseline)

**Files to Modify**:
- `src/cohezion/swarm/persistent_cache.py` (extend from above)

**Owner**: integration-engineer or performance-engineer

**Effort**: 2-4 hours

---

## Measurement & Validation

### Tools Available
- ✅ `metrics_collector.py` - Hardware monitoring
- ✅ `performance_baseline.py` - Before/after comparison
- ✅ `batch_sizing.py` - Safe concurrency limits

### Validation Checklist

**Concurrency (45% gain expected)**:
- [ ] Measure baseline throughput (4 concurrent)
- [ ] Increase to 8, measure improvement
- [ ] Verify thermal stays <75%
- [ ] Verify VRAM stays <80%
- [ ] Log when concurrency adjusts
- [ ] Expected: 45% throughput gain

**Persistence (15% gain expected)**:
- [ ] Measure cache hit rate before (expect 24.5%)
- [ ] After persistent cache, measure (expect 30-40%)
- [ ] Verify session restore works
- [ ] Measure disk I/O impact (should be <5%)
- [ ] Expected: 15% throughput gain

**LRU Eviction (combined gain)**:
- [ ] Monitor cache size over time
- [ ] Verify eviction triggers at threshold
- [ ] Measure hit rate with bounded cache
- [ ] Verify VRAM stays under control
- [ ] Expected: 1.81× combined improvement

### Reporting

Generate report using baseline profiler:
```python
profiler = PerformanceBaselineProfiler(Path("phase_1_results"))
baseline = profiler.run_full_profile()  # Before
# ... apply Phase 1 changes ...
after = profiler.run_full_profile()     # After

improvement_factor = after['throughput']['tokens_per_second'] / baseline['throughput']['tokens_per_second']
print(f"Phase 1 Improvement: {improvement_factor:.2f}×")
```

---

## Timeline

**Day 1 (Morning)**: Concurrency gate (2-4h)
- Implement DynamicConcurrencyGate
- Integrate into TokenEfficientClient
- Test with metrics_collector
- Measure throughput improvement

**Day 1 (Afternoon)**: Persistent cache (4-6h)
- Implement PersistentCache with JSONL
- Integration into TokenEfficientClient
- Test session restore
- Measure cache hit rate improvement

**Day 2 (Full)**: LRU eviction + validation (6-8h)
- Implement LRUPersistentCache
- Integrate metrics tracking
- Validate all three improvements
- Generate report + lessons learned

**Total**: 12-18 hours = 1.5-2 sprint days

---

## Success Criteria

✅ **Concurrency**: 45% throughput gain confirmed
✅ **Persistence**: Session cache working, hit rate improved 15%
✅ **LRU Eviction**: Cache bounded, hit rate stable
✅ **Combined**: 1.81× baseline improvement measured
✅ **Safety**: Thermal/VRAM stay within limits
✅ **Report**: Generated for stakeholders

---

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Thermal spike | metrics_collector + fallback to 4 | integration-engineer |
| VRAM pressure | LRU eviction + monitoring | performance-engineer |
| Lost cache entries | JSONL persistence + redundancy | integration-engineer |
| Disk I/O bottleneck | Batch writes, async persistence | integration-engineer |
| Hit rate drop | Monitor closely, tune eviction threshold | performance-engineer |

---

## Next Phase Preparation

Phase 1 success enables Phase 2 (1.86× additional improvement):
- Semantic cache + fuzzy matching
- Batch processing infrastructure
- Request deduplication
- **Total by Phase 2**: 3.37× baseline (1.81 × 1.86)

---

## Dependencies

✅ metrics_collector.py - Ready
✅ performance_baseline.py - Ready
✅ batch_sizing.py - Ready
✅ hardware_profiler_stub.py - Ready

**All dependencies satisfied. Phase 1 is unblocked.**

---

## Owner Assignment

- **integration-engineer**: Concurrency gate + persistent cache (primary)
- **performance-engineer**: LRU eviction + measurement (secondary)
- **test-specialist**: Validation + reporting

---

## Approval Gate

Once Phase 1 is complete:
1. Generate before/after metrics
2. Validate 1.81× improvement
3. Architecture-designer uses results for Phase 2 design
4. Proceed to Phase 2 (semantic cache + batching)

**Phase 1 is the proof point. It will unlock confidence for aggressive Phase 2+3 optimization.**

