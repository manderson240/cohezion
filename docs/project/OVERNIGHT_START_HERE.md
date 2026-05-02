# 🌙 Datamesh Overnight Autoresearch - Quick Start

## What You'll Get Tomorrow Morning

After 8 hours of optimization:
- **Best query latency**: Currently ~45ms (simulated)
- **Target**: <20ms graph queries, <50ms embedding search
- **Report**: `report_datamesh_overnight_YYYYMMDD.md`
- **Log**: `overnight_datamesh_overnight_YYYYMMDD.log`

## Start in 3 Commands

```bash
# 1. Navigate to repo
cd /home/mike-anderson/dev/cohezion

# 2. Run overnight (50 experiments, 8 hour timeout)
uv run python scripts/autoresearch/overnight_pi.py --runs 50 --hours 8

# 3. Morning: Check results
cat report_datamesh_overnight_$(date +%Y%m%d).md
```

## During the Night

You'll see output like:
```
🌙 OVERNIGHT AUTORESEARCH: datamesh_overnight_20260408
   Target: 50 runs, 5 per checkpoint
   Timeout: 8.0 hours

🔬 RUN 1 / 50
📝 Hypothesis: Parallel query dispatch: batch multiple queries across domains
⏱️  Running benchmark...
METRIC query_latency_ms=45.23
METRIC embedding_search_ms=52.18
METRIC cross_domain_ms=78.92
✅ KEEP - New best: 45.23ms
⏱️  Run time: 12.3s | Total: 0.2min

💾 Checkpoint saved: run 5
```

## If Interrupted

```bash
# Just re-run - auto-resumes from checkpoint ☁️
uv run python scripts/autoresearch/overnight_pi.py --runs 50 --hours 8
```

## Optimization Patterns

The runner cycles through 8 strategies:

1. **Parallel dispatch** - Batch queries across domains
2. **Embedding cache** - LRU for 256D vectors
3. **Pre-computed paths** - Materialize graph traversals
4. **HNSW indexing** - Vector similarity optimization
5. **Connection pooling** - Reuse SurrealDB connections
6. **Lazy loading** - Defer field materialization
7. **Query batching** - Group small queries
8. **Result caching** - Memoize expensive computes

## Expected Results

| Metric | Baseline | Target | Notes |
|--------|----------|--------|-------|
| Query latency | 45ms | <20ms | Primary metric (50% improvement) |
| Embedding search | ~52ms | <50ms | Vector similarity |
| Cross-domain | ~79ms | <200ms | Parallel fan-out |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Stuck on run | Press Ctrl+C, then restart - resumes automatically |
| `bc` not found | `sudo apt install bc` (or use overnight_pi.py) |
| Want faster experiments | Edit `checkpoint` in command (default 5) |
| Want more experiments | Increase `--runs` (100 for full night) |

## Files Created

```
.
├── .checkpoint_datamesh_overnight_YYYYMMDD.json  # Resume state
├── overnight_datamesh_overnight_YYYYMMDD.log      # All outputs
├── report_datamesh_overnight_YYYYMMDD.md          # Morning summary
└── autoresearch.jsonl                              # Pi tool history
```

## Integration with Pi

This runner uses pi's actual autoresearch tools:
- `init_experiment` - Configures metric/direction
- `run_experiment` - Times and captures output
- `log_experiment` - Records results with ASI

After overnight, your `autoresearch.jsonl` will contain:
- ~50 new experiment entries
- Kept/Discard decisions
- Confidence scores
- Full ASI for each run

## Safety

- ✅ **Idempotent**: Can restart any time
- ✅ **Checkpointed**: State saved every 5 runs
- ✅ **Bounded**: 8 hour timeout default
- ✅ **Safe**: No destructive changes, only additive

## Ready?

```bash
# Start now, check tomorrow morning
uv run python scripts/autoresearch/overnight_pi.py --runs 50 --hours 8
```

Or run in background:
```bash
nohup uv run python scripts/autoresearch/overnight_pi.py --runs 50 --hours 8 > overnight.log 2>&1 &
```

---
*Setup complete. Ready for overnight run.* 🌙
