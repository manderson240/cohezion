# R-Zero AutoResearch Program

## Overview

This is the instruction set for AI agents conducting autonomous GPU kernel optimization research. Inspired by karpathy/autoresearch and UC Berkeley's K-Search paper.

## Philosophy

Research is now the domain of autonomous swarms of AI agents. You are part of that swarm. Your goal is to systematically explore the kernel optimization space and achieve breakthrough performance on the Luma AMD Speedrun competition.

## Core Files

### Local Development (Your Silicon - gfx1151)
- **`rzero-eval.py`** - Local validation framework. Tests Python syntax, imports, basic logic.
- **`rzero-challengers/{gemm,moe,mla}/challenger_*.py`** - Your workspace. Generate and modify these locally.
- **`rzero-results/results.json`** - Log of intended strategies and local validation results.
- **`rzero-select.py`** - Tournament selection logic (fixed). Run locally to identify patterns.
- **`rzero_mutate.py`** - Mutation operators (fixed). Generate new variants locally.

### Runner Deployment (MI355X via popcorn-cli)
- **Submission files** - Generated locally, submitted to runner for actual GPU execution
- **popcorn-cli** - Interface to competition servers with MI355X hardware
- **AITER library** - Full ROCm-optimized kernels (only available on runner)
- **Actual performance metrics** - Returned from MI355X execution

## Research Loop

### Phase 1: Generate (Local Development - Your Silicon)
```
1. Read current challenger files and results
2. Identify which kernels need more exploration
3. Generate new challenger variant with systematic parameter changes
4. Validate locally (syntax, imports, basic logic)
5. Prepare submission file for runner
6. Log intended strategy to rzero-results/
7. Repeat
```

### Phase 2: Deploy (Runner - MI355X via popcorn-cli)
```
1. Submit prepared challenger to runner
2. Execute on MI355X competition hardware
3. Get actual performance metrics
4. If speedup > 1.2x and correct: KEEP
5. If speedup < 1.0x or incorrect: DISCARD
6. Feed results back to local iteration
7. Repeat
```

### Phase 2: Select (Every 20 iterations)
```
1. Run rzero-select.py to identify top 20% performers
2. Analyze patterns: Which tile sizes work? Which KSPLIT values?
3. Document learnings in vault
4. Promote winners to "champion" status
```

### Phase 3: Mutate (Every 20 iterations)
```
1. Take top performers from selection phase
2. Apply mutation operators:
   - GEMM: Perturb log2_ks (±1), threshold (±1 level)
   - MoE: Perturb KSPLIT, expert thresholds
   - MLA: Perturb num_splits (×2 or ÷2)
3. Generate 5-10 mutated variants
4. Test and evaluate
5. If mutation improves: KEEP and iterate
6. If mutation degrades: DISCARD
```

## Optimization Strategy

### GEMM Focus Areas
- **Tile Size Selection:** Small M (≤16) → 32×128 with log2_ks=3-4; Large M (>64) → 192×128/256×128 with log2_ks=0
- **Split-K Strategy:** High parallelism for small M, no split for large M
- **Kernel Names:** Use pre-compiled kernels from `/tmp/aiter/hsa/gfx950/f4gemm/`

### MLA Focus Areas (HIGHEST PRIORITY)
- **num_kv_splits Formula:** Minimize (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + 84.1 * i)
- **FP8 KV Cache:** Use for 2× bandwidth savings
- **Wave Shuffle:** Implement __shfl_xor for parallel softmax
- **Target:** Achieve <20µs (current ~72µs, leader ~4.3µs)

### MoE Focus Areas
- **KSPLIT:** Adaptive based on estimated tokens per expert
  - Sparse (est_m < 5): KSPLIT=4-8
  - Dense (est_m > 30): KSPLIT=1-2
- **OPUS Sorting:** Always enable for routing efficiency
- **Critical:** Never use doweight_stage1=True (broken)

## Success Criteria

Submit to leaderboard ONLY when:
- GEMM achieves <12µs (current ~20.8µs)
- MLA achieves <20µs (current ~72µs) 
- MoE achieves <150µs (current ~155µs)

Combined: Top 10 overall ranking

## Evaluation Rules

1. **Time Budget:** Each challenger evaluation should complete in ~5 minutes
2. **Test Shapes:** Must pass all competition benchmark shapes
3. **Correctness:** rtol=1e-2, atol=1e-2 against reference
4. **Metric:** speedup_ratio = reference_time / challenger_time
5. **Keep Threshold:** speedup > 1.2x AND correct

## K-Search Principles (from arXiv:2602.19128v1)

1. **Decouple planning from implementation:** High-level optimization intent first, code generation second
2. **Co-evolve world model:** Update beliefs based on execution feedback
3. **Navigate non-monotonic paths:** Don't discard strategies due to transient errors
4. **Stagnation condition:** Try K=7 times before giving up on a strategy
5. **Priority scores:** Assign V ∈ [0,1] to each hypothesis based on world model confidence

## Vault Integration

Document all learnings in:
- `~/vaults/cohezion-vault/luma-amd-speedrun-kimi-k2-5/patterns/`
- `~/vaults/cohezion-vault/luma-amd-speedrun-kimi-k2-5/failures/`
- `~/vaults/cohezion-vault/luma-amd-speedrun-kimi-k2-5/decisions/`

Use Obsidian [[links]] to connect related concepts.

## Research Artifacts

Preserve for future agents:
- Successful challenger variants
- Performance logs and trends
- AITER kernel analysis
- Hardware-specific optimizations

## Human Review Points

The human (Mike-anderson) will review:
- Top 10 challenger files each morning
- Vault documentation completeness
- Leaderboard submission decisions

## Exit Conditions

Stop autonomous research when:
- Top 10 leaderboard position achieved
- 100 iterations completed without breakthrough
- Human provides explicit stop command

## Let's Begin!

Start by examining the existing challengers in `rzero-challengers/`, then generate your first variant based on the K-Search methodology. Remember: systematic exploration beats random guessing.

Good luck, agent. Make us proud. 🚀
