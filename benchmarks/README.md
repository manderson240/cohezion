---
title: Kyutai Performance Benchmarking Guide
date: 2026-02-10
tags: [benchmarks, kyutai, mcp, performance, documentation]
aspect: thinker
neural:
  activation: 0.82
  stage: growing
  synapse_in: 0
  synapse_out: 4
---

# Kyutai Performance Benchmarking Guide

Comprehensive performance baseline capture and analysis for the [[kyutai-project|Kyutai]] [[mcp-model-context-protocol|MCP]] Server and Obsidian Plugin.

## Overview

This benchmarking suite captures detailed performance metrics across all system components:

- **MCP Server** (Python): Tool latencies, throughput, memory stability
- **Obsidian Plugin** (TypeScript): Load time, modal performance, network latency
- **Integration**: End-to-end workflow timing
- **System Resources**: CPU, memory, I/O profiles

## Quick Start

### Prerequisites

```bash
# Ensure MCP server is running
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server
python3 -m kyutai_mcp.main

# In another terminal, run benchmarks
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server/benchmarks
./run_benchmarks.sh
```

### Expected Runtime

- **Total**: 5-10 minutes
- **Python benchmarks**: 3-5 minutes
- **Report generation**: 1-2 minutes

## Benchmarking Framework

### 1. MCP Server Benchmarks (Python)

**File**: `benchmark_framework.py`

#### Capabilities

```
✓ Tool invocation latency (per tool, ms)
✓ Throughput under concurrent load (10/50/100 users)
✓ Memory usage (baseline, peak, stability)
✓ CPU utilization during inference
✓ I/O performance
✓ Network latency (HTTP)
```

#### Running Server Benchmarks

```bash
python3 benchmark_framework.py \
  --server-url http://localhost:8000 \
  --output metrics.json \
  --runs 10
```

#### Output

- `metrics.json`: Raw measurement data
- Console output: Summary statistics

#### Sample Output

```
[INFO] ─────────────────────────────────────────────
[INFO] KYUTAI MCP SERVER PERFORMANCE BENCHMARKS
[INFO] ─────────────────────────────────────────────

[INFO] Starting server latency tests (10 runs each)...
[INFO]   Testing health_check...
[INFO]   health_check: 25.34ms (median: 24.12ms)

[INFO] Starting throughput tests...
[INFO]   Testing 10 concurrent requests...
[INFO]     10 concurrent: 10/10 successful, avg 32.18ms

[INFO] Starting memory stability test (60s)...
[INFO]   Request 10: Memory 234.5MB
[INFO]   Request 20: Memory 235.2MB
...
```

### 2. Obsidian Plugin Benchmarks (TypeScript)

**File**: `benchmark-framework.ts`

#### Capabilities

```
✓ Plugin load time (startup)
✓ Modal window open time
✓ Settings pane load time
✓ Ribbon command response time
✓ Memory footprint (heap usage)
✓ Audio playback latency
✓ File upload/selection latency
```

#### Integration with Plugin

```typescript
import PluginBenchmarkSuite from './benchmarks/benchmark-framework';

// In plugin onload()
const benchmarks = new PluginBenchmarkSuite();
await benchmarks.initialize();

const results = await benchmarks.runAll({
  serverUrl: this.settings.api.serverUrl,
  modalElement: document.querySelector('.kyutai-modal'),
  settingsElement: document.querySelector('.kyutai-settings'),
});
```

#### Running Plugin Benchmarks

```bash
npm run bench
# or
npm test -- --bench
```

### 3. Integration Tests

**End-to-end workflow timing**

```bash
# Test complete workflows
./run_benchmarks.sh --test-workflows
```

Measures:
- Text → Speech latency
- Audio → Text latency
- Voice cloning latency
- Round-trip communication

## Performance Targets

| Component | Target | Phase | Notes |
|-----------|--------|-------|-------|
| Tool Invocation | <500ms | 1 | CPU-bound |
| TTS Generation | 50-200ms | 1 | Pocket TTS baseline |
| STT Transcription | 200-500ms | 2 | API-dependent |
| Plugin Startup | <2s | 1 | Asset loading |
| Modal Open | <500ms | 1 | DOM rendering |
| Audio Playback | <100ms | 1 | Browser native |
| Concurrent Users | 10+ | 1 | Graceful degradation |
| Memory (MCP) | <100MB | 1 | Idle baseline |
| Memory (Plugin) | <50MB delta | 1 | Heap growth |

## Measurements Explained

### Latency Metrics

```json
{
  "test_name": "speak_text",
  "latency": {
    "min_ms": 45.2,      // Fastest run
    "max_ms": 156.3,     // Slowest run
    "mean_ms": 98.5,     // Average
    "median_ms": 95.2,   // 50th percentile
    "p95_ms": 142.1,     // 95th percentile (worst 5%)
    "p99_ms": 154.8      // 99th percentile (worst 1%)
  }
}
```

### Throughput Metrics

```json
{
  "concurrent_50": {
    "successful": 48,
    "errors": 2,
    "error_rate": 0.04,
    "throughput_req_per_sec": 12.3,
    "latency": {
      "mean_ms": 95.2,
      "p95_ms": 142.1
    }
  }
}
```

### Memory Metrics

```json
{
  "memory": {
    "min_mb": 234.5,      // Lowest observed
    "max_mb": 289.3,      // Peak
    "mean_mb": 256.7,     // Average
    "delta_mb": 54.8      // Drift (max - min)
  },
  "stability": {
    "memory_drift_mb": 54.8,
    "is_stable": true     // < 50MB = stable
  }
}
```

## Understanding Results

### 1. Analyzing Latency

Look for:
- **Mean < P95**: Normal distribution (good)
- **Mean > P95**: Long tail of slow requests (investigate)
- **P99 >> P95**: Outliers/GC pauses (optimize or accept)

Example:
```
Mean: 98ms, P95: 142ms, P99: 155ms
→ 5% of requests take 142-155ms (acceptable)

Mean: 98ms, P95: 98ms, P99: 500ms
→ Outliers present (investigate)
```

### 2. Analyzing Throughput

Expected behavior:
- **10 concurrent**: ~100% success
- **50 concurrent**: ~95-99% success
- **100 concurrent**: Depends on resources

Example:
```
10 concurrent: 10/10 successful
50 concurrent: 48/50 successful (96% success)
100 concurrent: 85/100 successful (85% success)
→ Graceful degradation observed
```

### 3. Memory Stability

Good vs. Bad:
```
GOOD:
  Min: 234MB, Max: 245MB, Delta: 11MB
  → Stable, < 50MB drift

BAD:
  Min: 234MB, Max: 450MB, Delta: 216MB
  → Memory leak or unbounded growth
```

## Reports Generated

### 1. `baseline-performance.md`

Comprehensive human-readable report with:
- Executive summary
- Latency tables (all tools)
- Throughput analysis
- Memory profiles
- Bottleneck identification
- Optimization recommendations
- Reproducibility instructions

### 2. `metrics.json`

Machine-readable raw data:
- Individual run times
- Aggregated statistics
- Environment metadata
- Timestamp information

Use for:
- Trend analysis over time
- Automated performance gates
- Historical comparison

### 3. `recommendations.md`

Optimization guidance:
- Quick wins (immediate improvements)
- Medium-term improvements (Phase 2)
- Long-term architecture changes (Phase 3+)
- Monitoring strategy
- Testing approach

### 4. `system-info.json`

Environment metadata:
- OS and kernel version
- CPU/memory configuration
- Python version
- Test timestamp

Use for:
- Reproducibility
- Comparing across machines
- Identifying environmental factors

## Baseline Comparison

Track improvements across versions:

```bash
# Initial baseline (Feb 10, 2026)
cp metrics.json metrics-baseline-2026-02-10.json

# After optimization
./run_benchmarks.sh

# Compare
python3 compare_baselines.py \
  metrics-baseline-2026-02-10.json \
  metrics.json
```

## Optimization Workflow

1. **Capture baseline** (current)
   ```bash
   ./run_benchmarks.sh
   cp metrics.json metrics-baseline.json
   ```

2. **Implement optimization**
   - Update code
   - Run tests
   - Verify functionality

3. **Measure improvement**
   ```bash
   ./run_benchmarks.sh
   ```

4. **Compare results**
   - P95 latency reduction?
   - Memory improvement?
   - Throughput increase?

5. **Document findings**
   - Update recommendations.md
   - Add results to daily note
   - Commit improvements

## Performance Gates (CI/CD)

Add to test pipeline:

```bash
# Gate 1: Latency regression
P95_LATENCY=$(jq '.benchmarks.latency.speak_text.p95_ms' metrics.json)
if (( $(echo "$P95_LATENCY > 500" | bc -l) )); then
  echo "FAIL: P95 latency regression"
  exit 1
fi

# Gate 2: Memory stability
MEMORY_DELTA=$(jq '.benchmarks.memory_stability.memory.delta_mb' metrics.json)
if (( $(echo "$MEMORY_DELTA > 50" | bc -l) )); then
  echo "FAIL: Memory stability issue"
  exit 1
fi

# Gate 3: Error rate
ERROR_RATE=$(jq '.benchmarks.throughput.concurrent_50.error_rate' metrics.json)
if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
  echo "FAIL: Error rate > 1%"
  exit 1
fi
```

## Troubleshooting

### Issue: "MCP server not responding"

```bash
# Check if server is running
curl http://localhost:8000/health

# Start server if needed
cd /home/mike-anderson/vaults/cohezion-vault/mcp-server
python3 -m kyutai_mcp.main
```

### Issue: "No successful measurements"

```bash
# Check server logs
tail -f /tmp/kyutai-mcp.log

# Verify network connectivity
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_models", "params": {}}'
```

### Issue: High latency variance

Possible causes:
- [ ] System under load
- [ ] GC pauses (Python)
- [ ] Network interference
- [ ] Disk I/O contention

Solutions:
- Isolate system (stop other processes)
- Increase runs for better statistics
- Check system load: `top`, `vmstat`
- Verify network: `ping localhost:8000`

### Issue: Memory not decreasing

Possible causes:
- [ ] Model kept in memory
- [ ] Memory leak in service
- [ ] GC not running

Solutions:
- Check model initialization
- Use memory profiler: `python3 -m memory_profiler`
- Force GC between runs

## Advanced Usage

### Custom Benchmarks

Extend `BenchmarkSuite` for custom tests:

```python
class CustomBenchmark(BenchmarkSuite):
    async def test_custom_workflow(self):
        """Measure custom workflow."""
        durations = []
        for run in range(10):
            # Your custom test here
            duration = measure_operation(...)
            durations.append(duration)

        return self.calculate_metrics('custom_workflow', durations)
```

### Profiling

Capture detailed CPU/memory profiles:

```bash
# CPU profiling
python3 -m cProfile -s cumtime benchmark_framework.py

# Memory profiling
python3 -m memory_profiler benchmark_framework.py
```

### Load Testing

Generate sustained load:

```bash
# 1000 requests over 5 minutes
./run_benchmarks.sh --load-test \
  --duration 300 \
  --rate 200  # requests per second
```

## Integration with Version Control

Recommended workflow:

```bash
# Commit benchmarks with code changes
git add benchmarks/baseline-performance.md
git add benchmarks/metrics.json
git commit -m "feat: TTS optimization - 30% latency reduction

Performance improvements:
- TTS latency: 145ms → 98ms (-32%)
- P95 latency: 198ms → 142ms (-28%)
- Memory: +5MB (acceptable)"
```

## References

- **Kyutai**: https://www.kyutai.org/
- **Performance**: https://www.brendangregg.com/systems-performance-2nd-edition.html
- **Python Async**: https://docs.python.org/3/library/asyncio.html
- **Browser Performance**: https://developer.mozilla.org/en-US/docs/Web/API/Performance

## Version History

| Date | Version | Notes |
|------|---------|-------|
| 2026-02-10 | 1.0 | Initial baseline framework |
| TBD | 1.1 | GPU acceleration benchmarks |
| TBD | 1.2 | WebSocket streaming tests |
| TBD | 2.0 | Distributed load testing |

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review system-info.json for environment details
3. Check MCP server logs
4. Inspect metrics.json for detailed data

---

**Last Updated**: 2026-02-10
**Status**: Phase 1 - Baseline capture framework
**Next Steps**: Execute benchmarks, capture baselines, implement Phase 2 optimizations

## Related
- [[kyutai-project]]
- [[mcp-model-context-protocol]]
- [[api-design]]
- [[cloud-vault-mcp]]
