# Luma AMD Speedrun — Leaderboard Status
**Last Updated:** 2026-04-05 03:30 UTC | **Deadline:** April 6, 2026

## Competition Scores (hidden on CLI, check web leaderboard)

All submissions show `score: -` in popcorn-cli — scores are only visible on the competition website. All submissions passed all stages (test + benchmark + leaderboard).

## Latest Leaderboard Submissions

| Kernel | Submission ID | Time (UTC) | Status | Benchmark Performance |
|--------|--------------|-----------|--------|----------------------|
| **GEMM** | #730941 | 02:36 | passed | 13.3-33.4µs (v6 hybrid) |
| **MoE** | #729992 | 00:25 | passed | 89-436µs (dispatch_policy=1) |
| **MLA** | #731234 | 03:12 | passed | 23-304µs (hybrid_v3 einsum+wrapper) |

## Performance vs Leaders

| Kernel | Our Best | Leader | Gap | Path to Close |
|--------|----------|--------|-----|--------------|
| GEMM | 13.3µs | 4.3µs | 3.1× | 256×256 LDS tiles + ping-pong |
| MoE | 89µs (best shape) | 107µs | Competitive! | Some shapes beat leader |
| MLA | 23µs (best shape) | 12.7µs | 1.8× | Custom Split-K GEMV kernel |

## Submission History (Session 91 only)

### GEMM (amd-mxfp4-mm)
- **#730941** (02:36) — v6 hybrid: MFMA for small shapes, aiter for large. **LATEST**
- #730122 (00:42) — v5: launch_bounds + cache (13.3µs, first to beat aiter)
- #729728 (23:44) — LDS benchmark
- Earlier: v4, v3, v1 iterations + probe submissions

### MoE (amd-moe-mxfp4)
- **#729992** (00:25) — dispatch_policy=1 (37% worst-case improvement). **LATEST**
- #731184 (03:07) — dispatch_policy=2 test (marginal improvement)
- #731014 (02:47) — dispatch1+expert_mask test (fails on 256 experts)

### MLA (amd-mixed-mla)
- **#731234** (03:12) — hybrid_v3 (expanded einsum threshold). **LATEST**
- #730281 (01:04) — hybrid_v2 (wrapper + improved routing)
- Earlier: ASM-only, wrapper-only experiments

## Key Discoveries This Session

1. **FP4 MFMA register type**: `int ext_vector_type(8)` not `uint8_t ext_vector_type(16)`
2. **E8M0 scale formula**: `bf16_exp - 2 + (mantissa >= 96 ? 1 : 0)` 
3. **FP4 round-to-nearest-even**: `<=` at even midpoints (0.25, 1.25, 2.5, 5.0)
4. **e8m0_unshuffle**: Reverse CK ASM scale permutation
5. **dispatch_policy=1**: 37% MoE worst-case improvement
6. **Python overhead reduction**: id() caching + output pre-alloc saved 6µs
7. **Fused quant is WRONG path**: 4× bandwidth penalty outweighs quant savings
8. **LDS needs 256×256 tiles**: 32×32 too small, LDS overhead > MFMA compute

## Files to Preserve

### Active Submissions (DO NOT MODIFY)
- `amd-mxfp4-mm/submission_fp4mfma_v6.py` — GEMM leaderboard
- `amd-moe-mxfp4/submission_moe_dispatch_policy.py` — MoE leaderboard
- `amd-mixed-mla/submission_hybrid_v2.py` — MLA leaderboard

### Skills Created
- `.claude/skills/gfx950-mfma-register-layouts/SKILL.md`
- `.claude/skills/amd-moe-dispatch-policy/SKILL.md`
- `.claude/skills/gpu-kernel-python-overhead-reduction/SKILL.md`

### Vault
- `~/vaults/cohezion-vault/cerebellum/2026-04-04-session-91-mfma-breakthrough.md`

### Session Report
- `luma_speedrun/SESSION_91_FINAL.md`
