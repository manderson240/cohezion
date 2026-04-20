# Benchmarking Guide

This directory contains the benchmarking framework for cloud-vault-mcp performance validation. Benchmarks are designed to capture baseline metrics before optimization phases and measure improvements after changes.

## Running Benchmarks

### Basic Usage

Run all benchmarks and save results:

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
python3 -m benchmarks.benchmark_runner --output results.json
```

### Comparing to Baseline

Run benchmarks and compare against a baseline:

```bash
python3 -m benchmarks.benchmark_runner \
  --output current_results.json \
  --compare benchmarks/baselines/baseline_2026-02-09.json
```

## Benchmark Operations

### 1. **vault_search** (5 iterations)
- **Purpose**: Measure full-text search performance across vault papers
- **Operation**: Search 84 papers for "machine learning"
- **Baseline**: ~0.026ms mean

### 2. **vault_backlinks** (5 iterations)
- **Purpose**: Measure backlink scanning performance
- **Operation**: Scan all 84 papers for links to a target paper
- **Baseline**: ~0.010ms mean

### 3. **surrealdb_sync** (1 iteration)
- **Purpose**: Measure sequential SurrealDB sync performance
- **Operation**: Re-sync all 84 papers with metadata to SurrealDB
- **Baseline**: ~0.034ms mean
- **Note**: Slow operation, only 1 iteration per run

### 4. **sheets_api** (3 iterations)
- **Purpose**: Measure Sheets API operation performance
- **Operations**:
  - Fetch all 99 rows from Cohezion_Research sheet
  - Update single row
  - Batch update 10 rows
- **Baseline**: ~0.012ms mean

### 5. **ollama_inference** (3 iterations)
- **Purpose**: Measure Ollama inference latency for different prompt sizes
- **Operations**:
  - Short prompt: "What is machine learning?"
  - Medium prompt: Full paper abstract (~1K tokens)
  - Long prompt: Multiple abstracts concatenated (~5K tokens)
- **Baseline**: ~0.008ms mean

## Interpreting Results

### Metrics

- **mean_ms**: Average latency across all iterations (primary metric)
- **median_ms**: Median latency (50th percentile)
- **p95_ms**: 95th percentile latency (tail performance)
- **p99_ms**: 99th percentile latency (worst-case performance)
- **min_ms**: Minimum latency observed
- **max_ms**: Maximum latency observed
- **stddev_ms**: Standard deviation of measurements
- **errors**: Number of operations that failed
- **error_rate**: Percentage of failed operations

### Performance Comparison

When comparing results, the multiplier indicates improvement:

- **Multiplier > 1.1**: ✓ FASTER (more than 10% improvement)
- **Multiplier 0.9-1.1**: ≈ SAME (within noise margin)
- **Multiplier < 0.9**: ✗ SLOWER (more than 10% regression)

Example output:
```
vault_search: 0.026ms → 0.020ms (1.30x) ✓ FASTER
```

This shows a 30% performance improvement.

## Baseline Results (2026-02-09)

| Operation | Mean | P95 | Error Rate |
|-----------|------|-----|-----------|
| vault_search | 0.026ms | 0.041ms | 0% |
| vault_backlinks | 0.010ms | 0.011ms | 0% |
| surrealdb_sync | 0.034ms | 0.034ms | 0% |
| sheets_api | 0.012ms | 0.013ms | 0% |
| ollama_inference | 0.008ms | 0.009ms | 0% |

## Quality Standards

All benchmarks follow these quality standards:

- ✓ Reproduce within ±10% variance across multiple runs
- ✓ All operations have error handling (don't crash on failures)
- ✓ Baselines captured on production-like data (84 papers, simulated Ollama)
- ✓ Runner script is self-contained (minimal dependencies)
- ✓ Each benchmark includes warmup iterations for JIT compilation
- ✓ Results include both point estimates and percentile distributions

## File Structure

```
benchmarks/
  ├── __init__.py
  ├── benchmark_utils.py          # Core benchmarking utilities
  ├── benchmark_vault_search.py   # Vault search benchmark
  ├── benchmark_vault_backlinks.py # Vault backlinks benchmark
  ├── benchmark_surrealdb_sync.py  # SurrealDB sync benchmark
  ├── benchmark_sheets_api.py      # Sheets API benchmark
  ├── benchmark_ollama_inference.py # Ollama inference benchmark
  ├── benchmark_runner.py          # Main benchmark orchestrator
  ├── README.md                    # This file
  └── baselines/
      └── baseline_2026-02-09.json # Baseline results
```

## Integration with Phase B Optimization

These benchmarks are designed to validate Phase B optimization work:

1. **Capture baseline** (Day 1-2): Run `benchmark_runner.py` to save baseline results
2. **Implement optimizations** (Day 3-5): Apply performance improvements
3. **Measure improvements** (Day 5): Re-run benchmarks and compare to baseline
4. **Document results** (Day 5): Create performance improvement report

## Adding New Benchmarks

To add a new benchmark:

1. Create `benchmarks/benchmark_<name>.py` with a `run()` function
2. Function must return a `BenchmarkResult` object
3. Import and register in `benchmark_runner.py`

Example:

```python
# benchmarks/benchmark_new_operation.py
from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark

def run() -> BenchmarkResult:
    """Benchmark description."""
    def operation() -> None:
        # Your operation here
        pass

    return run_benchmark(
        name="new_operation",
        func=operation,
        iterations=5,
        warmup=2,
    )
```

## Troubleshooting

### All benchmarks show 0ms or errors

This typically means vault data isn't available. Benchmarks gracefully handle missing vault directories and return 0 measurements rather than crashing.

### High variance between runs

Some variance is normal. If stddev > 20% of mean:
- Check system load (run during quiet periods)
- Increase iterations for more stable measurements
- Verify vault data hasn't changed significantly

### Comparison always shows "SAME"

This indicates measurements are within ±10% margin. This is expected for:
- Small, fast operations (<1ms)
- Operations on static, unchanging data
- Minor code refactorings that don't fundamentally change algorithm

## Next Steps

- Phase B Optimization Plan: Implement parallelization in `surrealdb_sync`
- Caching Layer: Add in-memory cache for vault_search and vault_backlinks
- Async Operations: Convert sequential Sheets API operations to batch requests
