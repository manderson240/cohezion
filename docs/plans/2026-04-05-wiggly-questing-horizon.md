# Plan: Luma AMD Speedrun — Overnight Refinement (April 4-5, Deadline April 6)

## Context

Session 91 achieved breakthroughs on ALL THREE kernels with leaderboard submissions:

| Kernel | Session Start | Session End | Leader | Leaderboard |
|--------|-------------|------------|--------|-------------|
| GEMM | 13.4µs | **13.3µs** (v5, beat aiter!) | 4.3µs | v6 hybrid SUBMITTED |
| MoE | 88-695µs | **89-436µs** (dispatch_policy=1) | 107µs | SUBMITTED |
| MLA | ~70µs | **23-104µs** (hybrid_v2) | 12.7µs | SUBMITTED |

**Deadline: April 6, 2026.** Overnight refinement must be autonomous, rate-limit-aware (10/hr global), and preserve all progress.

## Overnight Strategy: Ralph Loop with Systematic Iteration

### Approach: Automated iteration loop testing one optimization per cycle

Each cycle:
1. Pick next optimization from the queue
2. Apply to kernel submission file
3. Test → if pass, benchmark → if improved, leaderboard submit
4. Log results to vault
5. Repeat

### GEMM Optimization Queue (priority order)

| # | Optimization | Expected Impact | File |
|---|-------------|----------------|------|
| 1 | **64×64 tile with 4 waves** (256 threads, 4 MFMA tiles per K iter) | 2-4× kernel speedup | `submission_fp4mfma_v7.py` |
| 2 | **buffer_load intrinsics** for branchless boundary (no if-checks) | 10-20% | In v7 |
| 3 | **K-split parallelism** for M=8 shapes (4-8 K-blocks) | 50% on small-M shapes | `submission_fp4mfma_v8.py` |
| 4 | **sched_group_barrier** for MFMA/load overlap scheduling | 10-20% | In v7/v8 |
| 5 | **GLOBAL_LOAD_LDS** 128-bit async transfers (CDNA4 feature) | 2× memory throughput | Advanced |

**Current best files:**
- `submission_fp4mfma_v5.py` — 13.3µs, beat aiter (custom-only)
- `submission_fp4mfma_v6.py` — hybrid routing (SUBMITTED to leaderboard)

### MoE Optimization Queue

| # | Optimization | Expected Impact |
|---|-------------|----------------|
| 1 | **dispatch_policy=2** + benchmark comparison | ~3% marginal |
| 2 | **Try dispatch_policy=3,4** if they exist | Unknown |
| 3 | **ck_moe_stage1/stage2 direct dispatch** with pre-sorted tokens | Bypass fused_moe overhead |
| 4 | **Expert-parallel custom kernel** via load_inline | Major rewrite, high risk |

**Current best:** `submission_moe_dispatch_policy.py` (policy=1, SUBMITTED)

### MLA Optimization Queue

| # | Optimization | Expected Impact |
|---|-------------|----------------|
| 1 | **Benchmark hybrid_v3** (expanded einsum threshold=65536) | Better small-shape coverage |
| 2 | **BF16 Q path** — skip FP8 quantization for small batches | Save ~3µs on Q quant |
| 3 | **Pre-compute metadata** once at module load for common shapes | Save ~5µs for cached shapes |
| 4 | **Custom Split-K GEMV kernel** via load_inline | The real breakthrough path |

**Current best:** `submission_hybrid_v2.py` (SUBMITTED)

### Rate Limit Strategy

10 submissions/hour global. Budget per cycle:
- 1 test (verify correctness)
- 1 benchmark (measure timing)
- 1 leaderboard (only if benchmark shows improvement over current best)
- Rotate: GEMM → MoE → MLA → GEMM

### Key Files (Current Best Submissions)

| Kernel | Current Best | Leaderboard File |
|--------|-------------|-----------------|
| GEMM | `submission_fp4mfma_v6.py` | Same (hybrid) |
| MoE | `submission_moe_dispatch_policy.py` | Same (policy=1) |
| MLA | `submission_hybrid_v2.py` | Same |

### Knowledge Preserved In

| Location | Content |
|----------|---------|
| `luma_speedrun/SESSION_91_FINAL.md` | Complete session report |
| `~/vaults/cohezion-vault/cerebellum/2026-04-04-session-91-mfma-breakthrough.md` | Vault entry |
| `.claude/skills/gfx950-mfma-register-layouts/SKILL.md` | FP4 MFMA register types, E8M0 formula |
| `.claude/skills/amd-moe-dispatch-policy/SKILL.md` | dispatch_policy discovery |
| `.claude/skills/gpu-kernel-python-overhead-reduction/SKILL.md` | Caching patterns |

### Verification

1. Each kernel change: `popcorn --mode test` (4/4 or 3/3 pass required)
2. Improvement check: `popcorn --mode benchmark` (must beat current best)
3. Leaderboard: `popcorn --mode leaderboard` (only after benchmark confirms gain)
4. Save all results to `luma_speedrun/overnight_results.md`
