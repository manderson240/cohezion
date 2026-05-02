# Autoresearch: K-Search Autonomous Kernel Optimization

Autonomous overnight experiment loop for the AMD E2E Model Speedrun competition.
Synthesizes K-Search (tree-structured optimization) with popcorn-cli evaluation
to systematically explore kernel parameter configurations on the MI355X runner.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  driver.py (main loop)               │
│                                                      │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ K-Search │→ │ Template   │→ │ popcorn-cli      │ │
│  │ Tree     │  │ Generator  │  │ test → benchmark │ │
│  │ SELECT   │  │            │  │ → leaderboard    │ │
│  └────┬─────┘  └────────────┘  └────────┬─────────┘ │
│       │                                  │           │
│       └──── UPDATE/INSERT/PRUNE ←────────┘           │
│             (results analysis)                       │
│                                                      │
│  Rate limiter: 1 leaderboard/hr/problem              │
│  Budget: ~75 cycles/night (8 min/cycle)              │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
cd research/challenges/luma_amd_speedrun/autoresearch

# Dry run (no popcorn-cli needed, validates templates):
uv run python driver.py --dry-run --max-cycles 5

# Single kernel sprint:
uv run python driver.py --kernel moe --max-cycles 20

# Full overnight run (all 3 kernels, priority-weighted):
uv run python driver.py

# Limit cycles:
uv run python driver.py --max-cycles 50
```

## File Structure

```
autoresearch/
├── driver.py              # Main overnight experiment loop
├── ksearch_tree.py        # K-Search tree (KNode, SELECT/INSERT/UPDATE/PRUNE)
├── generator.py           # Template-based submission.py generator
├── evaluator.py           # Wraps popcorn-cli (test/benchmark/leaderboard)
├── analyzer.py            # Result analysis → tree priority updates
├── rate_limiter.py        # 1/hour/problem leaderboard gating
├── templates/
│   ├── gemm_template.py   # Parameterized GEMM ($KERNEL_TABLE, $DEFAULT_LOG2_KS)
│   ├── moe_template.py    # Parameterized MoE ($KSPLIT_TABLE, $DEFAULT_KSPLIT)
│   └── mla_template.py    # Parameterized MLA ($SPLITS_TABLE, $KV_FORMAT, $FAST_MODE)
├── tree/
│   ├── gemm_tree.json     # Pre-seeded K-Search tree (11 nodes)
│   ├── moe_tree.json      # Pre-seeded K-Search tree (11 nodes)
│   └── mla_tree.json      # Pre-seeded K-Search tree (14 nodes)
└── results/
    ├── gemm_runs.jsonl     # Experiment log (append-only)
    ├── moe_runs.jsonl
    └── mla_runs.jsonl
```

## How It Works

### 1. K-Search Tree (`ksearch_tree.py`)

Each kernel has a tree of "strategy" nodes. Each node encodes:
- **strategy**: Human-readable description (e.g., "E=257,d=256,bs=16: sweep KSPLIT 1-6")
- **parameters**: JSON dict for template substitution (e.g., `{"KSPLIT_TABLE": {...}}`)
- **priority**: 0.0-1.0, used for selection (higher = more likely to be tried next)
- **stagnation_count**: Incremented on non-improving attempts; pruned at K=7

Operations:
- **SELECT**: Pick highest-priority active leaf node
- **UPDATE**: Record benchmark result, adjust priority, track stagnation
- **PRUNE**: Auto-prune after 7 stagnant attempts (K=7 threshold)
- **DECAY**: Periodically decay all priorities to encourage exploration

### 2. Templates (`templates/`)

Each template is a Python string with `$PARAM` substitution slots. The key innovation
is **per-shape lookup tables**: instead of one KSPLIT for all shapes, each shape gets
its own configuration.

Template parameters:
- **MoE**: `$KSPLIT_TABLE` (dict: "E_dexpert_bs" → KSPLIT value), `$DEFAULT_KSPLIT`
- **GEMM**: `$KERNEL_TABLE` (dict: "M_N_K" → {kernel, log2_ks}), `$DEFAULT_KERNEL`
- **MLA**: `$SPLITS_TABLE` (dict: "bs_kvseqlen" → num_splits), `$KV_FORMAT`, `$FAST_MODE`

### 3. Evaluator (`evaluator.py`)

Wraps `~/.local/bin/popcorn-cli submit`:
- **test**: Correctness check (no rate limit)
- **benchmark**: Per-shape timing + geomean (no rate limit)
- **leaderboard**: Official score (1/hour/problem limit)

Every variant runs test first; benchmark only on pass. Leaderboard only on new best.

### 4. Driver Loop (`driver.py`)

Each cycle (~8 minutes):
1. **Select kernel** (priority-weighted: MoE 50%, GEMM 30%, MLA 20%)
2. **SELECT** best node from kernel's K-Search tree
3. **Generate** submission.py from template + node parameters
4. **Test** via popcorn-cli (correctness check)
5. **Benchmark** if test passes (get per-shape timings)
6. **Analyze** results, update tree priorities
7. **Log** to JSONL (crash-safe, append-only)
8. **Leaderboard** submit if new best AND rate limit allows
9. Sleep 5s, repeat

### 5. Parameter Perturbation

After a node's first attempt, the driver slightly perturbs parameters on subsequent
attempts to explore the neighborhood:
- MoE: Random KSPLIT ±1-2 for random shape
- GEMM: Random log2_ks ±1 or kernel swap for random shape
- MLA: Random splits ×2, ÷2, or ±4 for random shape

## Kernel-Specific Search Spaces

### MoE (7 benchmark shapes, gap: 1.27x)
Primary lever: Per-shape KSPLIT lookup table. Values 0-6.
Key shapes: E=257 (256 routed + 1 shared) and E=33 (32 routed + 1 shared).

### GEMM (6 benchmark shapes, gap: 2.4x)
Primary lever: Per-shape kernel selection (gemm_a4w4 vs gemm_a4w4_asm) + split-K (log2_ks 0-4).
Key shapes: M=4 (bandwidth-bound) and M=256 (compute-bound).

### MLA (8 benchmark shapes, gap: 15.6x)
Primary lever: Adaptive num_kv_splits per (bs, kvseqlen). Also: FP8 vs MXFP4 KV format.
Key shapes: bs=4/kv=1024 (few splits) to bs=128/kv=8192 (many splits).

## Results Analysis

```bash
# View latest results
tail -5 results/moe_runs.jsonl | uv run python -m json.tool

# Find best result per kernel
uv run python -c "
from analyzer import get_best_result
from pathlib import Path
for k in ['moe', 'gemm', 'mla']:
    best = get_best_result(Path(f'results/{k}_runs.jsonl'))
    if best: print(f'{k}: {best[\"geomean_us\"]:.1f}µs')
    else: print(f'{k}: no results yet')
"

# View tree stats
uv run python -c "
from ksearch_tree import KSearchTree
from pathlib import Path
for k in ['moe', 'gemm', 'mla']:
    t = KSearchTree.load(Path(f'tree/{k}_tree.json'))
    print(t)
"
```

## Dead Ends (DO NOT RETRY)

- `doweight_stage1=True` — 82% mismatch or GPU crash
- `torch.compile(fused_moe)` — assertion crash on ROCm 7.1
- Pure Triton kernels — 50-70% slower than CK/ASM
- hiprtc compilation — blocked by runner
- `expert_mask=bincount` — GPU memory fault
- `num_kv_splits=64+` — exceeds aiter limits
- `AITER_JIT_DIR` pre-caching — internal error 1

## Coordination

This system is registered in `COORDINATION.md` as the `autoresearch` session.
It follows the staging directory protocol: backups are saved to `kernels/<kernel>/staging/`
before overwriting `submission.py`. The rate limiter enforces 1 leaderboard submission
per hour per problem to avoid API abuse.
