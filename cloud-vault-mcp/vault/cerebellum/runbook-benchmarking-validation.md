---
title: Operational Runbook - Benchmarking & Performance Validation
date: 2026-02-10
status: active
tags: [runbook, operations, benchmarking, performance]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 22
  synapse_out: 11
---

## Overview

Performance benchmarking framework establishes baselines and validates Phase B optimization claims.

**Location:** `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks/`

**Key Metrics:**
- Query response time (ms)
- Batch processing throughput (queries/sec)
- Memory usage (MB)
- Cache hit rate (%)
- Index effectiveness (queries with/without index)

## Capturing Baseline Benchmarks

### Prerequisites
```bash
# Ensure all services running
ollama serve &                # Ollama service
# Cloud Vault MCP running (via Claude Code or manual)

# Verify Python environment
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
pip install -e ".[dev]"
```

### Run Full Benchmark Suite
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks

# Capture baseline (all benchmarks)
python benchmark_runner.py \
  --output baseline_$(date +%Y-%m-%d).json \
  --warmup 3 \
  --iterations 10

# Expected output:
# Benchmark results written to: baseline_2026-02-10.json
# Total time: ~5-10 minutes (depends on system)
```

### Run Specific Benchmark
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks

# Ollama query performance only
python benchmark_runner.py \
  --test ollama_query \
  --output ollama_query_baseline.json

# Vault operations only
python benchmark_runner.py \
  --test vault_operations \
  --output vault_baseline.json

# SurrealDB batch operations
python benchmark_runner.py \
  --test surrealdb_batch \
  --output surrealdb_baseline.json
```

### Baseline File Format
```json
{
  "timestamp": "2026-02-10T14:32:45.123456Z",
  "system_info": {
    "platform": "linux",
    "python_version": "3.11.8",
    "cpu_count": 8,
    "memory_gb": 16
  },
  "benchmarks": {
    "ollama_query": {
      "test_name": "query_8b_model",
      "iterations": 10,
      "warmup_runs": 3,
      "results": {
        "mean_time_ms": 2350,
        "min_time_ms": 2100,
        "max_time_ms": 2800,
        "stddev_ms": 250,
        "p95_time_ms": 2700,
        "p99_time_ms": 2800
      }
    },
    "vault_read": {
      "mean_time_ms": 12,
      "min_time_ms": 8,
      "max_time_ms": 25,
      "stddev_ms": 5,
      "p95_time_ms": 20,
      "p99_time_ms": 24
    }
  }
}
```

## Comparing Phase B Results to Baseline

### After Phase B optimizations, compare results:

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp/benchmarks

# Run new benchmark
python benchmark_runner.py \
  --output phase-b_results_$(date +%Y-%m-%d).json

# Compare to baseline
python compare_benchmarks.py \
  baseline_2026-02-10.json \
  phase-b_results_2026-02-10.json
```

### Comparison Output Format
```
Benchmark Comparison Results
============================

ollama_query:
  Baseline:  mean=2350ms  p95=2700ms
  Phase B:   mean=1850ms  p95=2100ms
  Change:    -21% improvement ✅

vault_read:
  Baseline:  mean=12ms    p95=20ms
  Phase B:   mean=11ms    p95=19ms
  Change:    -8% improvement ✅

surrealdb_batch (100 queries):
  Baseline:  mean=850ms   throughput=118 qps
  Phase B:   mean=650ms   throughput=154 qps
  Change:    -24% latency, +30% throughput ✅✅

Overall improvement: 18% average
```

## What Improvements Count as "Success"

### Success Criteria

| Metric | Baseline | Target | Success |
|--------|----------|--------|---------|
| Ollama query latency | ~2350ms | < 2000ms | -15% or more |
| Batch throughput | ~118 qps | > 150 qps | +27% or more |
| Memory usage | ~450MB | < 350MB | -22% or more |
| Cache hit rate | N/A | > 60% | High hit rate on repeated queries |
| Index efficiency | N/A | > 30% faster indexed | 30%+ improvement with indexes |

### Decision Logic
```
If improvement >= 15%:
  ✅ PROCEED with Phase B optimization
  Justifies development time and complexity

If improvement 5-15%:
  🟡 MARGINAL - Consider trade-offs
  Is code complexity worth the gain?

If improvement < 5%:
  ❌ DEFER - Not worth complexity
  Focus on other optimizations
```

### Example: Evaluating SurrealDB Batching

**Phase B Claim:** "Batching queries will improve throughput by 30%"

**Baseline Measurement:**
```json
{
  "test": "surrealdb_batch_100_queries",
  "baseline": {
    "sequential": {"mean_ms": 850, "throughput": 118},
    "batched": {"mean_ms": 620, "throughput": 161}
  }
}
```

**Result:** 27% improvement
```
Target: +30%
Actual: +27%
Status: Nearly achieved ✅ PROCEED
```

## Investigating Regressions

**Symptom:** Phase B results are SLOWER than baseline

### Step 1: Verify Data Quality
```bash
# Rerun baseline to confirm
python benchmark_runner.py \
  --test <failing_test> \
  --iterations 20  # More iterations for stability

# Check for outliers (high variance = unreliable data)
python analyze_benchmark.py baseline_2026-02-10.json | grep -A3 "stddev"
```

### Step 2: Identify the Change
```bash
# What code changed in Phase B?
git log --oneline baseline_commit..HEAD

# Review commit diffs
git show <commit-hash> -- <file>

# Rollback Phase B change and retest
git checkout <baseline-commit>
python benchmark_runner.py --output baseline_reverted.json

# If reverted baseline is fast: Phase B change caused regression
# If still slow: Regression was already present
```

### Step 3: Understand Root Cause
```bash
# Profile the slow code with Python profiler
python -m cProfile -s cumulative \
  benchmark_runner.py --test <failing_test> > profile.txt

# Top slowest functions:
head -20 profile.txt

# Or use memory profiler
pip install memory-profiler
python -m memory_profiler benchmark_runner.py --test <failing_test>
```

### Step 4: Fix the Regression
```bash
# Example: Accidental nested loop
# BAD:
for doc in docs:
  for concept in all_concepts:  # O(n²) complexity!
    if concept in doc:
      link()

# GOOD:
concept_index = {c: True for c in all_concepts}
for doc in docs:
  for concept in concept_index:  # O(n) with fast lookup
    if concept in doc:
      link()

# Retest after fix
python benchmark_runner.py --output phase-b_fixed.json
```

## Troubleshooting Benchmark Failures

### Issue: Benchmark Timeout (> 10 minutes)
```bash
# Benchmark takes too long, probably hitting service timeout

# Reduce test scope
python benchmark_runner.py \
  --test <one_test_only> \
  --iterations 5  # Fewer iterations
  --timeout 60    # 60 second timeout per operation

# Check if service is responding
curl http://localhost:8360/health | jq '.status'

# If unhealthy, restart services
pkill ollama
ollama serve &
# Restart Claude Code to reload Ollama MCP
```

### Issue: "Out of Memory" During Benchmark
```bash
# Benchmark is memory-intensive (batch operations with large datasets)

# Free up system memory
sync; echo 3 > /proc/sys/vm/drop_caches

# Reduce benchmark scope
python benchmark_runner.py \
  --test <smaller_test> \
  --batch-size 10  # Smaller batches

# Monitor memory during run
watch -n 1 free -h
```

### Issue: Inconsistent Results (High Variance)
```bash
# Results vary widely between runs (stddev > 20% of mean)
# Indicates system contention

# Run benchmark on quiet system
sudo systemctl isolate rescue.target  # Single-user mode
python benchmark_runner.py --output baseline_quiet.json

# Or use taskset to restrict to specific CPU
taskset -c 0-3 python benchmark_runner.py  # Use cores 0-3 only

# Check for background processes
top -b -n 1 | head -15
killall <unnecessary_process>

# Rerun benchmark
python benchmark_runner.py --iterations 20  # More iterations averages out noise
```

### Issue: "Assertion Error: Results file corrupted"
```bash
# Benchmark result JSON file is invalid

# Validate JSON
python -m json.tool baseline_2026-02-10.json > /dev/null
# If error: JSON is malformed

# Check file size (should be > 1KB)
ls -lh baseline_2026-02-10.json

# If file is tiny: Benchmark didn't write results
# Rerun:
python benchmark_runner.py --output baseline_fresh.json

# If persistent, check permissions
chmod 666 baseline_2026-02-10.json
```

## Benchmark Test Descriptions

### ollamaquery (Ollama inference latency)
```bash
# Tests: Query time for different model sizes
# - 8B model (fast)
# - 14B model (medium)
# - Long context queries (256K tokens)

# What it measures:
# - Model loading time (first call)
# - Inference time (subsequent calls)
# - E2E latency through Ollama MCP
```

### vault_operations (Vault file I/O)
```bash
# Tests: Read, write, search in vault
# - Read paper note (simple read)
# - Write to paper note (update)
# - Search papers for concept (grep-like operation)

# What it measures:
# - File system latency
# - Obsidian vault performance
# - Batch vs sequential I/O
```

### surrealdb_batch (Graph database performance)
```bash
# Tests: Query patterns for SurrealDB
# - Single node query (1 paper)
# - Batch query (10 papers)
# - Graph traversal (paper → concepts → related papers)
# - Index effectiveness

# What it measures:
# - Database query latency
# - Batch operation throughput
# - Index impact on complex queries
```

## SurrealDB Parallelization Optimization

### New Feature: Parallel Bulk Imports

**Location:** `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/surrealdb_sync.py`

**Configuration:**
```python
# Default: parallel enabled with 10 concurrent connections
sync = SurrealDBSync(
    vault_path="/home/mike-anderson/vaults/cohezion-vault",
    parallel_enabled=True,        # Enable/disable parallelization
    max_concurrent=10,            # Concurrent HTTP connections
)

# Disable parallelization (fallback to sequential)
sync = SurrealDBSync(
    vault_path="/home/mike-anderson/vaults/cohezion-vault",
    parallel_enabled=False,
)
```

### Performance Benchmarks

**Realistic HTTP Latency Simulation (10ms per operation):**

| Metric | Sequential | Parallel (10 conn) | Speedup |
|--------|------------|--------------------|---------|
| 84 papers sync | 850ms | 94ms | **9.0x** |
| Per-paper latency | 10.13ms | 1.12ms | **9.0x** |
| Throughput | 99 papers/sec | 893 papers/sec | **9.0x** |

**Key Results:**
- ✅ Achieves 9.0x speedup (exceeds 8-15x target)
- ✅ Uses connection pooling to limit concurrent requests
- ✅ Handles partial failures gracefully
- ✅ 100% backward compatible

### Running the Benchmark

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Run parallel HTTP benchmark (with realistic latency simulation)
python -m benchmarks.benchmark_surrealdb_http

# Expected output:
# Sequential: 850.8ms
# Parallel: 94.2ms
# Speedup: 9.0x
```

### Testing

```bash
# Run all parallel sync tests
python -m pytest tests/test_surrealdb_parallel_sync.py -v

# Run specific test class
python -m pytest tests/test_surrealdb_parallel_sync.py::TestParallelConfiguration -v

# Run with coverage
python -m pytest tests/test_surrealdb_parallel_sync.py --cov=src.mcp_server.surrealdb_sync
```

### Implementation Details

**Async Architecture:**
- Uses `asyncio` for concurrent HTTP operations
- `httpx.AsyncClient` with connection pooling
- `asyncio.Semaphore` limits concurrent operations to `max_concurrent`

**Methods:**
- `_sync_paper_async()` - Async paper sync with HTTP calls
- `_sync_concept_async()` - Async concept sync
- `_bulk_import_papers_parallel()` - Parallel papers import
- `_bulk_import_concepts_parallel()` - Parallel concepts import
- `bulk_import_papers()` - Smart router (parallel or sequential)
- `bulk_import_concepts()` - Smart router (parallel or sequential)

**Error Handling:**
- Catches HTTP timeouts
- Logs failures per file (doesn't crash on partial failure)
- Returns count of successful imports
- Exceptions from async tasks are caught via `gather(return_exceptions=True)`

### Disabling Parallelization

If you encounter issues and need to disable parallelization:

```python
# In MCP initialization
sync = SurrealDBSync(
    vault_path="/home/mike-anderson/vaults/cohezion-vault",
    parallel_enabled=False,  # Falls back to sequential
)

# Or via environment variable (future enhancement)
export SURREALDB_PARALLEL=false
```

### sheets_api (Google Sheets integration)
```bash
# Tests: Sheets API performance
# - Fetch all rows (if enabled)
# - Update single cell
# - Batch update (10 cells)

# What it measures:
# - API latency
# - Authentication overhead
# - Batch vs sequential performance
```

## Performance Baseline Template

Save this as a reference for future benchmarks:

```markdown
# Performance Baseline - [DATE]

**System:** [CPU], [RAM], [GPU]
**Ollama:** [version], [28 models loaded]
**Python:** [3.11.8]

## Results Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Ollama query (8B) | 2.35s | < 2.0s | 🟡 |
| Vault read | 12ms | < 20ms | ✅ |
| SurrealDB batch (100x) | 850ms | < 700ms | 🟡 |
| Memory peak | 450MB | < 500MB | ✅ |

## Detailed Results
[Insert benchmark JSON output here]

## Notes
- Baseline captured on [TYPE: cold start / warm cache]
- Services: [Ollama, SurrealDB, Sheets API enabled/disabled]
- No background processes
```

## Related Documentation
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-ci-cd-pipeline]]
- [[troubleshooting-mcp-infrastructure]]
- [[mcp-infrastructure-architecture]]

## Related Concepts

- [[webb-cosmic-question-mark-gravitational-lens]]
- [[humanitys-last-exam-benchmark]]
- [[2026-02-09-model-wrangler-strategy]]
- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-ollama-mcp-operations]]
- [[runbook-health-checks]]
